import asyncio
import os
from typing import Set, Dict, Any, Optional
import requests
import discord

class ApprovalView(discord.ui.View):
    def __init__(self, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.approved: Optional[bool] = None
        self.responder: Optional[discord.User] = None

    @discord.ui.button(label="Đồng ý thêm tag", style=discord.ButtonStyle.green, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.approved = True
        self.responder = interaction.user
        self.stop()
        # Vô hiệu hóa các nút sau khi chọn
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Bỏ qua", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.approved = False
        self.responder = interaction.user
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

class DiscordNotifier:
    def __init__(
        self,
        bot_token: str = "",
        channel_id: Optional[int] = None,
        webhook_url: str = "",
        timeout: int = 120
    ):
        self.bot_token = bot_token.strip() if bot_token else ""
        self.channel_id = channel_id
        self.webhook_url = webhook_url.strip() if webhook_url else ""
        self.timeout = timeout

        self.client: Optional[discord.Client] = None
        self.channel: Optional[discord.TextChannel] = None
        self._bg_task: Optional[asyncio.Task] = None
        self.is_ready = False

    async def start(self):
        """Khởi động Discord Bot Client nếu có cấu hình token."""
        if not self.bot_token or not self.channel_id:
            return

        intents = discord.Intents.default()
        self.client = discord.Client(intents=intents)

        @self.client.event
        async def on_ready():
            self.channel = self.client.get_channel(self.channel_id)
            self.is_ready = True
            print(f"[*] Discord Bot đã kết nối thành công: {self.client.user} (Kênh: #{getattr(self.channel, 'name', self.channel_id)})")

        self._bg_task = asyncio.create_task(self.client.start(self.bot_token))

        # Đợi bot kết nối sẵn sàng tối đa 15 giây
        for _ in range(30):
            if self.is_ready and self.channel is not None:
                break
            await asyncio.sleep(0.5)

        if not self.is_ready:
            print("[!] Cảnh báo: Discord Bot chưa thể kết nối hoặc không tìm thấy channel_id. Sẽ sử dụng fallback CLI.")

    async def close(self):
        """Đóng kết nối Discord khi kết thúc."""
        if self.client and not self.client.is_closed():
            await self.client.close()
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()

    async def ask_approval(self, post: Dict[str, Any], tags_to_add: Set[str], dry_run: bool = False) -> bool:
        """
        Gửi yêu cầu hỏi duyệt (Noti:ask) vào Discord và đợi phản hồi.
        Nếu Discord chưa kết nối, fallback hỏi trực tiếp trên Console CLI.
        """
        post_id = post.get("id")
        tags_str = ", ".join(sorted(list(tags_to_add)))
        danbooru_url = f"https://danbooru.donmai.us/posts/{post_id}"

        # 1. Nếu Discord Bot kết nối thành công -> Hỏi qua Discord Buttons
        if self.is_ready and self.channel:
            embed = discord.Embed(
                title=f"❓ [Xác nhận cập nhật Tag] Danbooru #{post_id}",
                url=danbooru_url,
                description=f"Hệ thống đề xuất thêm tag cho bài viết này.\n{'(Chế độ DRY_RUN mô phỏng)' if dry_run else ''}",
                color=discord.Color.gold()
            )
            embed.add_field(name="➕ Tag dự kiến THÊM", value=f"```\n{tags_str}\n```", inline=False)
            
            # Tóm tắt tag hiện tại
            curr_tags = post.get("tag_string", "")
            curr_preview = curr_tags[:300] + ("..." if len(curr_tags) > 300 else "")
            embed.add_field(name="📋 Tag hiện tại", value=f"```{curr_preview}```", inline=False)

            # Ảnh thumbnail bài viết
            preview_img = post.get("preview_file_url") or post.get("large_file_url") or post.get("file_url")
            if preview_img:
                embed.set_thumbnail(url=preview_img)

            embed.set_footer(text=f"⏱️ Hết hạn sau {self.timeout} giây nếu không có phản hồi.")

            view = ApprovalView(timeout=self.timeout)
            msg = await self.channel.send(embed=embed, view=view)

            print(f"  [Noti:ask] Đã gửi yêu cầu duyệt Post #{post_id} vào Discord. Đang chờ phản hồi...")
            await view.wait()

            if view.approved is True:
                embed.color = discord.Color.green()
                embed.title = f"✅ [ĐÃ CHẤP THUẬN] Danbooru #{post_id}"
                embed.set_footer(text=f"Được đồng ý bởi @{view.responder} • Tiến hành thêm tags")
                await msg.edit(embed=embed, view=view)
                return True
            elif view.approved is False:
                embed.color = discord.Color.red()
                embed.title = f"❌ [ĐÃ TỪ CHỐI] Danbooru #{post_id}"
                embed.set_footer(text=f"Đã bị từ chối bởi @{view.responder} • Bỏ qua bài này")
                await msg.edit(embed=embed, view=view)
                return False
            else:
                embed.color = discord.Color.dark_grey()
                embed.title = f"⏱️ [HẾT GIỜ DUYỆT] Danbooru #{post_id}"
                embed.set_footer(text=f"Hết {self.timeout}s không có phản hồi • Tự động bỏ qua")
                await msg.edit(embed=embed, view=view)
                return False

        # 2. Fallback CLI Console nếu Discord chưa cấu hình
        print(f"\n  [Noti:ask - CLI Fallback] Post #{post_id} ({danbooru_url})")
        print(f"  > Tag cần thêm: {tags_str}")
        try:
            choice = input(f"  > Bạn có đồng ý thêm tag cho Post #{post_id}? [y/N]: ").strip().lower()
            return choice in ("y", "yes")
        except Exception:
            return False

    async def send_notification(self, post: Dict[str, Any], tags_to_add: Set[str], success: bool = True, dry_run: bool = False):
        """
        Gửi thông báo kết quả cập nhật (Noti:discord).
        Hỗ trợ cả Discord Bot channel và Webhook.
        """
        post_id = post.get("id")
        tags_str = ", ".join(sorted(list(tags_to_add)))
        danbooru_url = f"https://danbooru.donmai.us/posts/{post_id}"

        title = f"📢 [Cập nhật Tag] Danbooru #{post_id}"
        if dry_run:
            title = f"📢 [DRY-RUN Mô phỏng] Danbooru #{post_id}"

        # 1. Gửi qua Discord Bot Channel
        if self.is_ready and self.channel:
            embed = discord.Embed(
                title=title,
                url=danbooru_url,
                color=discord.Color.blue() if not dry_run else discord.Color.orange()
            )
            embed.add_field(name="➕ Tags đã thêm", value=f"```\n{tags_str}\n```", inline=False)
            preview_img = post.get("preview_file_url") or post.get("large_file_url")
            if preview_img:
                embed.set_thumbnail(url=preview_img)
            await self.channel.send(embed=embed)
            return

        # 2. Gửi qua Discord Webhook (nếu có cấu hình)
        if self.webhook_url:
            payload = {
                "embeds": [{
                    "title": title,
                    "url": danbooru_url,
                    "color": 3447003 if not dry_run else 15105570,
                    "fields": [
                        {"name": "➕ Tags đã thêm", "value": f"```{tags_str}```"}
                    ]
                }]
            }
            try:
                requests.post(self.webhook_url, json=payload, timeout=10)
            except Exception as e:
                print(f"[!] Lỗi khi gửi Webhook Discord: {e}")
