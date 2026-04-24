import os, logging, asyncio, urllib.parse
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
import database as db

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8702277983:AAH5uO3PgpYN-G13aV9S461nqgu5s4M-UlM")
ADMIN_ID  = int(os.getenv("ADMIN_ID", "6198353113"))

# ── category maps ──────────────────────────────────────────
CAT_MAP     = {"Indian": "indian", "R@p": "premium", "Child": "movies", "All": "all"}
CAT_REVERSE = {v: k for k, v in CAT_MAP.items()}

# ── keyboards ──────────────────────────────────────────────
def admin_keyboard(admin_id=None):
    """Full admin keyboard. Notification button shows current state."""
    notify_label = "🔔 New User Notif: ON" if (admin_id is None or db.get_admin_notify(admin_id)) else "🔕 New User Notif: OFF"
    return ReplyKeyboardMarkup([
        ["Change UPI",           "Change Username"],
        ["Change Price",         "Add Links"],
        ["Change Premium Image", "Process Link Video"],
        ["Add Demo Video",       "Remove Demo"],
        ["Check Users List",     "Check History"],
        ["Set Proof Link"],
        ["➕ Add Admin",         "➖ Remove Admin"],
        ["👥 List Admins"],
        ["📢 Broadcast"],
        [notify_label],
    ], resize_keyboard=True)

USER_BOTTOM_KB = ReplyKeyboardMarkup([
    [KeyboardButton("Payment proofs 📋"), KeyboardButton("Payment done ✅")],
    [KeyboardButton("Get Premium 💎"),    KeyboardButton("Premium demo 🔥")],
], resize_keyboard=True)

CAT_KB = ReplyKeyboardMarkup([
    ["Indian", "R@p"],
    ["Child",  "All"],
], resize_keyboard=True)

# ── helpers ────────────────────────────────────────────────
def get_all_admins():
    """Returns list of all admin IDs - main + extra admins from DB."""
    try:
        s = db.all_settings()
        extra = s.get("extra_admins", "")
        extra_list = []
        if extra:
            for x in str(extra).split(","):
                x = x.strip()
                if x.isdigit():
                    extra_list.append(int(x))
        return [ADMIN_ID] + extra_list
    except:
        return [ADMIN_ID]

def is_admin(uid):
    return int(uid) in get_all_admins()

async def send_premium_categories(bot, chat_id):
    s = db.all_settings()
    pi = s.get("price_indian",  "59")
    pp = s.get("price_premium", "99")
    pm = s.get("price_movies",  "149")
    pa = s.get("price_all",     "249")
    img = s.get("premium_image", "https://i.ibb.co/9x38myC/x.jpg")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"👉𝗜𝗡𝗗𝗜𝗔𝗡 𝗗𝗔𝗦𝗜👈 - ₹{pi}",             callback_data="pay_indian")],
        [InlineKeyboardButton(f"🤤𝗥@𝗣 𝗩𝗜𝗗𝗘𝗢𝗦🤤 - ₹{pp}",               callback_data="pay_premium")],
        [InlineKeyboardButton(f"🫦𝗖𝗛𝗜𝗟𝗗 𝗩𝗜𝗗𝗘𝗢𝗦 (𝟱𝟬𝗞+)👈 - ₹{pm}",        callback_data="pay_movies")],
        [InlineKeyboardButton(f"🥵𝗔𝗟𝗟 𝗜𝗡 𝗢𝗡𝗘 𝟱𝟬+ 𝗚𝗥𝗢𝗨𝗣𝗦👈 - ₹{pa}",       callback_data="pay_all")],
    ])
    try:
        await bot.send_photo(chat_id=chat_id, photo=img, reply_markup=kb)
    except:
        await bot.send_message(chat_id=chat_id, text="💎 Choose Your Pack:", reply_markup=kb)

async def ask_for_screenshot(bot, chat_id):
    s = db.all_settings()
    db.set_state(chat_id, "wait_screenshot")
    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"📸 **𝙎𝙀𝙉𝘿 𝙎𝘾𝙍𝙀𝙀𝙉𝙎𝙃𝙊𝙏 𝙊𝙁 𝙔𝙊𝙐𝙍 𝙋𝘼𝙔𝙈𝙀𝙉𝙏 𝙁𝙊𝙍 𝙂𝙀𝙏 𝙋𝙍𝙀𝙈𝙄𝙐𝙈**\n\n"
            f"Support: {s.get('support','@support')}"
        ),
        parse_mode="Markdown"
    )

async def send_payment_qr(bot, chat_id, cat):
    import qrcode, io
    s     = db.all_settings()
    upi   = s.get("upi", "example@ybl")
    price = s.get(f"price_{cat}", "99")

    upi_data = f"upi://pay?pa={upi}&pn=Premium&am={price}&cu=INR"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(upi_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    pay_text = (
        f"🏷️ 𝐏𝐫𝐢𝐜𝐞: ₹{price}\n\n"
        f"⏳ 𝐓𝐢𝐦𝐞 𝐋𝐞𝐟𝐭: 02:00\n\n"
        f"1️⃣ 𝐒𝐜𝐚𝐧  |  2️⃣ 𝐏𝐚𝐲  |  3️⃣ 𝐂𝐥𝐢𝐜𝐤 'PAYMENT DONE'"
    )

    import urllib.parse as _up
    phonpe = f"https://phon.pe/ru_" + _up.quote(f"{upi}&am={price}", safe="")
    paytm  = f"https://paytm.com/biz/pay?pa={upi}&am={price}"
    gpay   = f"https://gpay.app.goo.gl/pay"
    fampay = f"https://fampay.in/"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 PhonePe ↗", url=phonpe),
         InlineKeyboardButton("💳 Paytm ↗",   url=paytm)],
        [InlineKeyboardButton("🔵 GPay ↗",    url=gpay),
         InlineKeyboardButton("💛 Fampay ↗",  url=fampay)],
        [InlineKeyboardButton("✅ PAYMENT DONE SEND SCREENSHOT", callback_data="done_ss")],
    ])

    db.set_state(chat_id, "wait_screenshot")

    try:
        await bot.send_photo(chat_id=chat_id, photo=buf, caption=pay_text,
                             parse_mode="Markdown", reply_markup=kb)
        log.info(f"✅ QR sent to {chat_id} for {cat} ₹{price}")
    except Exception as e:
        log.error(f"QR send error: {e}")
        await bot.send_message(chat_id=chat_id,
                               text=pay_text + f"\n\nUPI: `{upi}`",
                               parse_mode="Markdown", reply_markup=kb)


# ═══════════════════════════════════════════════════════════
#  /start
# ═══════════════════════════════════════════════════════════
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_new = db.add_user(user.id, user.first_name, user.username or "NoUsername")
    db.set_state(user.id, "none")

    if is_admin(user.id):
        role = "👑 Main Admin" if int(user.id) == ADMIN_ID else "👤 Sub Admin"
        await update.message.reply_text(
            f"Welcome {role}!\nBot developed by @nglynx",
            reply_markup=admin_keyboard(user.id)
        )
    else:
        # Notify admins who have new_user_notify ON
        if is_new:
            notify_text = (
                f"🆕 **New User Joined!**\n\n"
                f"👤 Name: {user.first_name}\n"
                f"🔗 Username: @{user.username or 'NoUsername'}\n"
                f"🆔 ID: `{user.id}`\n\n"
                f"📊 Total Users: {db.total_users()}"
            )
            for admin_id in get_all_admins():
                if db.get_admin_notify(admin_id):
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=notify_text,
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        log.error(f"New user notify error for admin {admin_id}: {e}")

        user_text = (
            "Available Videos Collection?\n\n"
            "1. Mom Son videos - 5000+\n"
            "2. Sister Brother videos - 2000+\n"
            "3. Cp kids videos - 15000+\n"
            "4. R@pe & Force videos - 3000+\n"
            "5. Teen Girl Videos - 6000+\n"
            "6. Indian Desi videos - 10000+\n"
            "7. Hidden cam videos - 2000+"
        )
        inline_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Get Premium",        callback_data="get_premium")],
            [InlineKeyboardButton("🥵 Demo Videos",        callback_data="view_demos")],
            [InlineKeyboardButton("✅ How To Get Premium", callback_data="how_to")],
        ])
        try:
            await update.message.reply_photo(
                photo="https://i.ibb.co/d4Ffygs4/x.jpg",
                caption=user_text,
                reply_markup=inline_kb
            )
        except:
            await update.message.reply_text(user_text, reply_markup=inline_kb)

        await update.message.reply_text("👇 Menu 👇", reply_markup=USER_BOTTOM_KB)


# ═══════════════════════════════════════════════════════════
#  /help  (admin only)
# ═══════════════════════════════════════════════════════════
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "🛠 **Admin Commands & Tools:**\n\n"
        "🔹 **Change UPI:** Update UPI ID.\n"
        "🔹 **Change Username:** Update @support shown to users.\n"
        "🔹 **Change Price / Add Links:** Modify prices and channel links.\n"
        "🔹 **Change Premium Image:** Customize 'Get Premium' image.\n"
        "🔹 **Add / Remove Demo:** Manage demo videos.\n"
        "🔹 **Check Users List:** See all users with IDs.\n"
        "🔹 **Check History:** See total approved/rejected payments.\n"
        "🔹 **📢 Broadcast:** Send message to all users.\n"
        "🔹 **🔔 New User Notif:** Toggle new user join notifications ON/OFF.",
        parse_mode="Markdown"
    )


# ═══════════════════════════════════════════════════════════
#  MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    message = update.message
    if not message:
        return

    db.add_user(user.id, user.first_name, user.username or "NoUsername")
    text  = message.text or ""
    photo = message.photo
    video = message.video
    state = db.get_state(user.id)
    adm   = is_admin(user.id)

    # ══ ADMIN STATE MACHINE ══════════════════════════════
    if adm:
        if state == "wait_add_admin" and text:
            new_id = text.strip()
            if new_id.lstrip("-").isdigit():
                s = db.all_settings()
                existing = s.get("extra_admins", "")
                ids = [x.strip() for x in str(existing).split(",") if x.strip()] if existing else []
                if new_id not in ids and int(new_id) != ADMIN_ID:
                    ids.append(new_id)
                    db.set_setting("extra_admins", ",".join(ids))
                db.set_state(user.id, "none")
                all_admins = get_all_admins()
                await message.reply_text(
                    f"✅ **Admin `{new_id}` added!**\n\n👥 All Admins: {len(all_admins)}",
                    parse_mode="Markdown", reply_markup=admin_keyboard(user.id)
                )
            else:
                await message.reply_text("❌ Send a valid Telegram User ID (numbers only)!")
            return

        if state == "wait_remove_admin" and text:
            rem_id = text.strip()
            if rem_id.lstrip("-").isdigit():
                if int(rem_id) == ADMIN_ID:
                    await message.reply_text("❌ Cannot remove main admin!")
                    return
                s = db.all_settings()
                existing = s.get("extra_admins", "")
                ids = [x.strip() for x in str(existing).split(",") if x.strip()] if existing else []
                if rem_id in ids:
                    ids.remove(rem_id)
                    db.set_setting("extra_admins", ",".join(ids))
                    await message.reply_text(f"✅ **Admin `{rem_id}` removed!**", parse_mode="Markdown", reply_markup=admin_keyboard(user.id))
                else:
                    await message.reply_text(f"❌ ID `{rem_id}` not in extra admins.", parse_mode="Markdown")
                db.set_state(user.id, "none")
            else:
                await message.reply_text("❌ Send a valid Telegram User ID!")
            return

        if state == "wait_proof_link" and text:
            db.set_setting("proof_link", text.strip())
            db.set_state(user.id, "none")
            await message.reply_text(f"✅ Proof link updated to: {text.strip()}", reply_markup=admin_keyboard(user.id))
            return

        if state == "wait_upi" and text:
            db.set_setting("upi", text)
            db.set_state(user.id, "none")
            await message.reply_text(f"✅ UPI updated to: {text}", reply_markup=admin_keyboard(user.id))
            return

        if state == "wait_username" and text:
            db.set_setting("support", text)
            db.set_state(user.id, "none")
            await message.reply_text(f"✅ Support username updated to: {text}", reply_markup=admin_keyboard(user.id))
            return

        if state == "wait_price_category" and text:
            if text in CAT_MAP:
                internal = CAT_MAP[text]
                db.set_state(user.id, f"wait_price_val_{internal}")
                await message.reply_text(
                    f"Send the new price for {text} category (Numbers only):",
                    reply_markup=ReplyKeyboardMarkup([["Cancel"]], resize_keyboard=True)
                )
            else:
                db.set_state(user.id, "none")
                await message.reply_text("❌ Cancelled.", reply_markup=admin_keyboard(user.id))
            return

        if state.startswith("wait_price_val_") and text:
            cat = state.replace("wait_price_val_", "")
            if text.isdigit():
                db.set_setting(f"price_{cat}", text)
                db.set_state(user.id, "none")
                display = CAT_REVERSE.get(cat, cat)
                await message.reply_text(f"✅ Price for {display} updated to ₹{text}!", reply_markup=admin_keyboard(user.id))
            else:
                await message.reply_text("❌ Numbers only please!")
            return

        if state == "wait_link_category" and text:
            if text in CAT_MAP:
                internal = CAT_MAP[text]
                db.set_state(user.id, f"wait_link_val_{internal}")
                await message.reply_text(f"Send the new private channel link for {text}:")
            else:
                db.set_state(user.id, "none")
                await message.reply_text("❌ Cancelled.", reply_markup=admin_keyboard(user.id))
            return

        if state.startswith("wait_link_val_") and text:
            cat = state.replace("wait_link_val_", "")
            db.set_setting(f"link_{cat}", text)
            db.set_state(user.id, "none")
            display = CAT_REVERSE.get(cat, cat)
            await message.reply_text(f"✅ Link for {display} updated!", reply_markup=admin_keyboard(user.id))
            return

        if state == "wait_demo_video" and video:
            db.add_demo(video.file_id)
            db.set_state(user.id, "none")
            await message.reply_text("✅ Demo video added successfully!", reply_markup=admin_keyboard(user.id))
            return

        if state == "wait_premium_image" and photo:
            db.set_setting("premium_image", photo[-1].file_id)
            db.set_state(user.id, "none")
            await message.reply_text("✅ Premium selection image updated!", reply_markup=admin_keyboard(user.id))
            return

        if state == "wait_how_to_video" and video:
            db.set_setting("how_to_video", video.file_id)
            db.set_state(user.id, "none")
            await message.reply_text("✅ 'How To Get Premium' video updated!", reply_markup=admin_keyboard(user.id))
            return

        if state == "wait_broadcast":
            db.set_state(user.id, "none")
            users   = db.get_all_users()
            ok = fail = 0
            for uid in users:
                try:
                    if photo:
                        await context.bot.send_photo(chat_id=uid, photo=photo[-1].file_id,
                                                      caption=message.caption or "")
                    elif video:
                        await context.bot.send_video(chat_id=uid, video=video.file_id,
                                                      caption=message.caption or "")
                    elif text:
                        await context.bot.send_message(chat_id=uid, text=text)
                    ok += 1
                except:
                    fail += 1
            await message.reply_text(
                f"📢 **Broadcast Done!**\n✅ Sent: {ok}\n❌ Failed: {fail}",
                parse_mode="Markdown", reply_markup=admin_keyboard(user.id)
            )
            return

    # ══ USER STATE: wait_screenshot ══════════════════════
    if state == "wait_screenshot" and photo:
        photo_id = photo[-1].file_id
        db.set_state(user.id, "none")
        s = db.all_settings()

        # Tell user payment is pending
        try:
            await context.bot.send_photo(
                chat_id=user.id,
                photo="https://i.ibb.co/ymm1Pvsv/x.png",
                caption=(
                    f"⏳ Screenshot has been sent for approval\n\n"
                    f"You will get private channel link within 20 minutes\n\n"
                    f"Contact support {s.get('support','@support')} ✅"
                )
            )
        except:
            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    f"⏳ Screenshot has been sent for approval\n\n"
                    f"You will get private channel link within 20 minutes\n\n"
                    f"Contact support {s.get('support','@support')} ✅"
                )
            )

        # ✅ FIX: Notify ALL admins with the payment screenshot
        admin_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}"),
            InlineKeyboardButton("❌ Reject",  callback_data=f"reject_{user.id}")
        ]])
        caption = (
            f"💰 **New Payment Verification**\n\n"
            f"👤 **User:** {user.first_name} (@{user.username or 'NoUsername'})\n"
            f"🆔 **ID:** `{user.id}`\n\n"
            f"✅ Approve or ❌ Reject?"
        )
        sent_count = 0
        for admin_id in get_all_admins():
            try:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_id,
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=admin_kb
                )
                sent_count += 1
                log.info(f"✅ Payment SS sent to admin {admin_id}")
            except Exception as e:
                log.error(f"❌ Failed to notify admin {admin_id}: {e}")

        if sent_count == 0:
            log.error("❌ Could not send payment SS to ANY admin!")
        return

    # ══ REPLY KEYBOARD BUTTONS ═══════════════════════════
    if text == "Get Premium 💎":
        await send_premium_categories(context.bot, user.id)
        return

    if text == "Payment done ✅":
        await ask_for_screenshot(context.bot, user.id)
        return

    if text == "Payment proofs 📋":
        s = db.all_settings()
        proof_link = s.get("proof_link", "")
        if proof_link:
            await message.reply_text(
                "**Payment Proofs ✅**\n\nClick below to view payment proofs:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📋 View Payment Proofs", url=proof_link)
                ]])
            )
        else:
            await message.reply_text("**Payment proofs channel not set yet.**\nContact support.", parse_mode="Markdown")
        return

    if text == "Premium demo 🔥":
        demos = db.get_demos()
        if not demos:
            await message.reply_text("**No demo videos available right now.**", parse_mode="Markdown")
        else:
            for (did, fid) in demos:
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("💎 Get Premium", callback_data="get_premium")
                ]])
                await context.bot.send_video(
                    chat_id=user.id, video=fid,
                    caption="🎬 **This video is only for demo**\n💎 Click Get Premium for VIP channels access",
                    parse_mode="Markdown",
                    reply_markup=kb
                )
        return

    # ══ ADMIN PANEL BUTTONS ═══════════════════════════════
    if adm:
        # New User Notification Toggle
        if "New User Notif" in text:
            current = db.get_admin_notify(user.id)
            new_state = not current
            db.set_admin_notify(user.id, new_state)
            status = "🔔 ON" if new_state else "🔕 OFF"
            await message.reply_text(
                f"✅ **New User Notifications: {status}**\n\n"
                f"{'You will now receive notifications when new users join.' if new_state else 'You will no longer receive notifications when new users join.'}",
                parse_mode="Markdown",
                reply_markup=admin_keyboard(user.id)
            )
            return

        if text == "Change UPI":
            db.set_state(user.id, "wait_upi")
            await message.reply_text("Send the new UPI ID:")

        elif text == "Change Username":
            db.set_state(user.id, "wait_username")
            await message.reply_text("Send new support username (e.g., @newname):")

        elif text == "Change Price":
            db.set_state(user.id, "wait_price_category")
            await message.reply_text("Which category price do you want to change?", reply_markup=CAT_KB)

        elif text == "Add Links":
            db.set_state(user.id, "wait_link_category")
            await message.reply_text("Which category link do you want to set?", reply_markup=CAT_KB)

        elif text == "Add Demo Video":
            db.set_state(user.id, "wait_demo_video")
            await message.reply_text("Send the video you want to add as a demo now:")

        elif text == "Remove Demo":
            demos = db.get_demos()
            if not demos:
                await message.reply_text("No demo videos currently available.")
            else:
                for (did, fid) in demos:
                    kb = InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ Delete Demo", callback_data=f"deldemo_{did}")
                    ]])
                    await context.bot.send_video(
                        chat_id=user.id, video=fid,
                        caption=f"Demo Video #{did}", reply_markup=kb
                    )

        elif text == "Change Premium Image":
            db.set_state(user.id, "wait_premium_image")
            await message.reply_text("Send the new image for the Premium Section now:")

        elif text == "Process Link Video":
            db.set_state(user.id, "wait_how_to_video")
            await message.reply_text("Send the video for 'How to Get Premium' now:")

        elif text == "Check Users List":
            details = db.get_user_details()
            count   = len(details)
            lines   = [f"👤 {r['name']} (@{r['username']})\n🆔 `{r['user_id']}`" for r in reversed(details)][:30]
            msg     = f"📊 **Total Bot Users:** {count}\n\n" + "\n\n".join(lines)
            if count > 30:
                msg += "\n\n... (Showing last 30 users)"
            await message.reply_text(msg, parse_mode="Markdown")

        elif text == "Check History":
            h = db.get_history()
            await message.reply_text(
                f"📈 **Payment History:**\n✅ Approved: {h.get('approved',0)}\n❌ Rejected: {h.get('rejected',0)}",
                parse_mode="Markdown"
            )

        elif text == "Set Proof Link":
            db.set_state(user.id, "wait_proof_link")
            await message.reply_text("Send the channel/group link for Payment Proofs:")

        elif text == "➕ Add Admin":
            db.set_state(user.id, "wait_add_admin")
            all_admins = get_all_admins()
            await message.reply_text(
                f"👤 **Add New Admin**\n\n"
                f"Current admins: {len(all_admins)}\n\n"
                f"Send the Telegram **User ID** of the new admin:",
                parse_mode="Markdown"
            )

        elif text == "➖ Remove Admin":
            db.set_state(user.id, "wait_remove_admin")
            s = db.all_settings()
            extra = s.get("extra_admins", "")
            ids = [x.strip() for x in str(extra).split(",") if x.strip()] if extra else []
            if not ids:
                await message.reply_text("No extra admins to remove.")
                db.set_state(user.id, "none")
            else:
                list_txt = "\n".join([f"• `{i}`" for i in ids])
                await message.reply_text(
                    f"👥 **Extra Admins:**\n{list_txt}\n\nSend User ID to remove:",
                    parse_mode="Markdown"
                )

        elif text == "👥 List Admins":
            all_admins = get_all_admins()
            lines = []
            for aid in all_admins:
                notify_status = "🔔" if db.get_admin_notify(aid) else "🔕"
                if aid == ADMIN_ID:
                    lines.append(f"👑 **Main Admin:** `{aid}` {notify_status}")
                else:
                    lines.append(f"👤 **Sub Admin:** `{aid}` {notify_status}")
            await message.reply_text(
                f"👥 **All Admins ({len(all_admins)}):**\n\n" + "\n".join(lines) +
                f"\n\n{notify_status} = New user notification status",
                parse_mode="Markdown"
            )

        elif text == "📢 Broadcast":
            db.set_state(user.id, "wait_broadcast")
            await message.reply_text(
                "📢 Send your broadcast message now.\n(Text, Photo with caption, or Video with caption)"
            )


# ═══════════════════════════════════════════════════════════
#  CALLBACK HANDLER
# ═══════════════════════════════════════════════════════════
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data    = query.data
    chat_id = query.message.chat_id
    user    = query.from_user
    s       = db.all_settings()

    if data == "get_premium":
        await send_premium_categories(context.bot, chat_id)

    elif data == "done_ss":
        db.set_state(chat_id, "wait_screenshot")
        await context.bot.send_message(
            chat_id=chat_id,
            text="📸 **SEND SCREENSHOT OF YOUR PAYMENT**\n\nSend your screenshot now 👇",
            parse_mode="Markdown"
        )

    elif data == "how_to":
        vid = s.get("how_to_video", "")
        if vid:
            await context.bot.send_video(
                chat_id=chat_id, video=vid,
                caption="✅ **How To Get Premium / Process Link**\nWatch this video to understand the process.",
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(chat_id=chat_id,
                                            text="Video not available. Contact support.")

    elif data == "view_demos":
        demos = db.get_demos()
        if not demos:
            await context.bot.send_message(chat_id=chat_id,
                                            text="No demo videos available right now.")
        else:
            for (did, fid) in demos:
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("👉 Get Premium", callback_data="get_premium")
                ]])
                await context.bot.send_video(
                    chat_id=chat_id, video=fid,
                    caption="🎬 This video is only for demo\n💎 Click Get Premium for VIP channels access",
                    reply_markup=kb
                )

    elif data.startswith("pay_"):
        cat = data.replace("pay_", "")
        await send_payment_qr(context.bot, chat_id, cat)

    elif data.startswith("deldemo_"):
        did = int(data.replace("deldemo_", ""))
        db.del_demo(did)
        try:
            await query.edit_message_caption(caption="✅ Demo video deleted!")
        except:
            pass

    elif data.startswith("approve_"):
        # ✅ Any admin can approve
        if not is_admin(user.id):
            await query.answer("Not authorized!", show_alert=True)
            return
        target  = int(data.replace("approve_", ""))
        support = s.get("support", "@support")
        db.inc_history("approved")

        l_indian  = s.get("link_indian",  "https://t.me/link1")
        l_premium = s.get("link_premium", "https://t.me/link2")
        l_movies  = s.get("link_movies",  "https://t.me/link3")
        l_all     = s.get("link_all",     "https://t.me/link4")

        approval_text = (
            f"✅ **YOUR PAYMENT IS SUCCESSFULLY APPROVED**\n\n"
            f"Click below link to join private channel\n\n"
            f"Contact support {support}"
        )
        approval_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇮🇳 Indian Pack",  url=l_indian)],
            [InlineKeyboardButton("😈 R@p Pack",      url=l_premium)],
            [InlineKeyboardButton("👶 Child Pack",    url=l_movies)],
            [InlineKeyboardButton("🔥 All In One",   url=l_all)],
        ])

        try:
            await context.bot.send_message(
                chat_id=target,
                text=approval_text,
                parse_mode="Markdown",
                reply_markup=approval_kb
            )
        except Exception as e:
            log.error(f"Approve send error: {e}")

        # Update the message for THIS admin
        try:
            old_cap = query.message.caption or "Payment"
            await query.edit_message_caption(
                caption=old_cap + f"\n\n✅ APPROVED by @{user.username or user.id}",
                parse_mode="Markdown"
            )
        except:
            pass

        # Also notify other admins that it was approved
        approved_by = f"@{user.username}" if user.username else str(user.id)
        for admin_id in get_all_admins():
            if admin_id != user.id:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"✅ Payment for user `{target}` was **APPROVED** by {approved_by}",
                        parse_mode="Markdown"
                    )
                except:
                    pass

        await query.answer("✅ Approved! Link sent to user.", show_alert=True)

    elif data.startswith("reject_"):
        # ✅ Any admin can reject
        if not is_admin(user.id):
            await query.answer("Not authorized!", show_alert=True)
            return
        target = int(data.replace("reject_", ""))
        db.inc_history("rejected")

        try:
            await context.bot.send_message(
                chat_id=target,
                text=(
                    "❌ **Payment Rejected**\n\n"
                    "Your payment screenshot was not verified.\n"
                    "Please try again or contact support."
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            log.error(f"Reject send error: {e}")

        try:
            old_cap = query.message.caption or "Payment"
            await query.edit_message_caption(
                caption=old_cap + f"\n\n❌ REJECTED by @{user.username or user.id}",
                parse_mode="Markdown"
            )
        except:
            pass

        # Notify other admins
        rejected_by = f"@{user.username}" if user.username else str(user.id)
        for admin_id in get_all_admins():
            if admin_id != user.id:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"❌ Payment for user `{target}` was **REJECTED** by {rejected_by}",
                        parse_mode="Markdown"
                    )
                except:
                    pass

        await query.answer("❌ Rejected! User notified.", show_alert=True)


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    print("✅ Bot running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
