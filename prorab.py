import os import asyncio import random from datetime import datetime, timedelta from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ( ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, )

TOKEN = os.getenv("TOKEN") ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

class Player: def init(self, user_id: int, name: str): self.user_id = user_id self.name = name self.balance = 1000 self.on_shift = False self.shift_end = None self.protection = 0  # процент защиты от штрафов

players: dict[int, Player] = {} transfer_states: dict[int, int] = {} broadcast_mode: set[int] = set()

================== МЕНЮ ==================

def main_menu(): return InlineKeyboardMarkup([ [InlineKeyboardButton("💰 Баланс", callback_data="balance")], [InlineKeyboardButton("🛠 Заработать", callback_data="earn")], [InlineKeyboardButton("🔁 Перевод", callback_data="transfer")], [InlineKeyboardButton("🏪 Магазин", callback_data="shop")], ])

================== СТАРТ ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user if user.id not in players: players[user.id] = Player(user.id, user.full_name) await update.message.reply_text( f"👷‍♂️ Добро пожаловать, {user.full_name}!\nБанк КаменскАвтодор открыт.", reply_markup=main_menu(), )

================== КНОПКИ ==================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE): q = update.callback_query await q.answer() uid = q.from_user.id

if uid not in players:
    await q.edit_message_text("Напиши /start")
    return

p = players[uid]

if q.data == "balance":
    await q.edit_message_text(f"💰 Баланс: {p.balance} ₽", reply_markup=main_menu())

elif q.data == "earn":
    if p.on_shift:
        await q.edit_message_text(f"⏳ Ты уже на смене до {p.shift_end.strftime('%H:%M:%S')}", reply_markup=main_menu())
        return
    p.on_shift = True
    shift_minutes = random.randint(5, 10)
    p.shift_end = datetime.now() + timedelta(minutes=shift_minutes)
    await q.edit_message_text(f"🛠 Ты на смене {shift_minutes} минут. Не отвлекайся!")

    async def end_shift():
        await asyncio.sleep(shift_minutes * 60)
        if not p.on_shift:
            return  # отменена из-за штрафа
        earned = random.randint(300, 900)
        p.balance += earned
        p.on_shift = False
        await context.bot.send_message(p.user_id, f"✅ Смена окончена. Ты заработал {earned} ₽")

    asyncio.create_task(end_shift())

elif q.data == "transfer":
    kb = [[InlineKeyboardButton(other.name, callback_data=f"to_{other.user_id}")]
          for other in players.values() if other.user_id != uid]
    if not kb:
        await q.edit_message_text("Некому переводить", reply_markup=main_menu())
    else:
        await q.edit_message_text("Выбери получателя:", reply_markup=InlineKeyboardMarkup(kb))

elif q.data.startswith("to_"):
    to_id = int(q.data.split("_")[1])
    transfer_states[uid] = to_id
    await q.edit_message_text("Введи сумму перевода числом:")

elif q.data == "shop":
    await q.edit_message_text(
        "🏪 Магазин\n1️⃣ Каска — 500 ₽ (снижает штрафы на 50%)\n2️⃣ Справка — 800 ₽ (отменяет 1 штраф)\n3️⃣ Связи — 1500 ₽ (иммунитет 1 час)\n4️⃣ Конверт — 300 ₽ (+5% к заработку)",
        reply_markup=main_menu(),
    )

================== ТЕКСТ ==================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): uid = update.effective_user.id text = update.message.text

# ===== Рассылка =====
if uid in broadcast_mode:
    sent = 0
    for p in players.values():
        try:
            await context.bot.send_message(p.user_id, f"📢 Рассылка:\n{text}")
            sent += 1
        except:
            pass
    broadcast_mode.remove(uid)
    await update.message.reply_text(f"✅ Рассылка отправлена ({sent} чел)")
    return

# ===== Перевод =====
if uid in transfer_states:
    try:
        amount = int(text)
    except ValueError:
        await update.message.reply_text("Введи число")
        return

    to_id = transfer_states.pop(uid)
    sender = players[uid]
    receiver = players.get(to_id)

    if amount <= 0 or amount > sender.balance:
        await update.message.reply_text("❌ Неверная сумма")
        return

    sender.balance -= amount
    receiver.balance += amount

    await update.message.reply_text(f"✅ Ты перевёл {amount} ₽ игроку {receiver.name}", reply_markup=main_menu())
    await context.bot.send_message(receiver.user_id, f"💸 Тебе перевели {amount} ₽ от {sender.name}")

================== РАССЫЛКА ==================

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.effective_user.id != ADMIN_ID: return broadcast_mode.add(update.effective_user.id) await update.message.reply_text("✉️ Введи текст для рассылки")

================== ШТРАФЫ ВИТАЛИКА ==================

async def vitalkin_fines(app): while True: await asyncio.sleep(random.randint(1200, 3600))  # 20-60 мин if players: victim = random.choice(list(players.values())) fine = random.randint(50, 300) effective_fine = int(fine * (1 - victim.protection/100)) victim.balance -= effective_fine victim.on_shift = False  # отменяет смену при штрафе try: await app.bot.send_message(victim.user_id, f"🚨 Прораб Виталик\nШтраф: –{effective_fine} ₽\nПричина: не внушаешь доверие") except: pass

================== ЗАПУСК ==================

async def main(): app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

asyncio.create_task(vitalkin_fines(app))

print("BOT STARTED")
await app.run_polling()

if name == "main": asyncio.run(main())