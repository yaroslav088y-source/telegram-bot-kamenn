import random
import time
import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.environ.get("TOKEN")  # переменная среды с токеном

users = {}
shop_items = {
    "Асфальтовая катка": 1000,
    "Щебень премиум": 500,
    "Каска прораба": 200
}

OWNER_ID = 5775839902  # <-- Твой Telegram ID для рассылок

# Пользователь
def get_user(uid, full_name):
    if uid not in users:
        users[uid] = {"name": full_name, "money": 1000, "items": [], "level": 1, "last_work": 0, "fines": []}
    return users[uid]

# Виталик
def vit_check(user):
    vit_chance = 0.15
    if "Щебень премиум" in user["items"]:
        vit_chance *= 0.9
    if random.random() < vit_chance:
        fine = random.randint(300, 2500)
        reason = random.choice([
            "не тот шрифт в журнале",
            "погода не по ГОСТу",
            "лицо слишком довольное",
            "документы лежали криво",
            "подозрительно ровный асфальт"
        ])
        user["money"] -= fine
        user["fines"].append(f"-{fine} ₽ за '{reason}'")
        return f"\n🚨 Проверка! Инспектор Виталик.\nНарушение: {reason}\nШтраф: -{fine} ₽"
    return ""

# Нижние кнопки
reply_buttons = ReplyKeyboardMarkup([
    [KeyboardButton("💰 Моя получка"), KeyboardButton("🏗 Заработать получку")],
    [KeyboardButton("📊 Профиль"), KeyboardButton("👥 Игроки банка")],
    [KeyboardButton("🔁 Перевести получку")]
], resize_keyboard=True)

# Inline меню
def inline_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Получка", callback_data="work")],
        [InlineKeyboardButton("🏗 Магазин", callback_data="shop")],
        [InlineKeyboardButton("🏦 Депозит", callback_data="deposit")],
        [InlineKeyboardButton("💳 Кредит", callback_data="credit")],
        [InlineKeyboardButton("🔁 Перевод", callback_data="transfer")]
    ])

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    full_name = update.effective_user.first_name + " " + (update.effective_user.last_name or "")
    user = get_user(update.effective_user.id, full_name)
    await update.message.reply_text(f"🏦 КаменскАвтодор АсфальтКапитал\nРаботяга: {user['name']}\nБаланс: {user['money']} ₽", reply_markup=inline_menu())
    await update.message.reply_text("Или используй нижние кнопки:", reply_markup=reply_buttons)

# Нижние кнопки
async def reply_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id, update.effective_user.first_name + " " + (update.effective_user.last_name or ""))
    text = update.message.text
    now = time.time()

    if text == "💰 Моя получка" or text == "🏗 Заработать получку":
        if now - user["last_work"] < 60:
            msg = "⏳ Смена ещё не закончилась"
        else:
            user["last_work"] = now
            pay_amount = random.randint(800, 1200)
            if "Асфальтовая катка" in user["items"]:
                pay_amount = int(pay_amount * 1.2)
            user["money"] += pay_amount
            msg = f"Получка: {pay_amount} ₽"
        msg += vit_check(user)
        await update.message.reply_text(msg + f"\nБаланс: {user['money']} ₽", reply_markup=inline_menu())

    elif text == "📊 Профиль":
        fines = "\n".join(user["fines"][-5:]) if user["fines"] else "Нет штрафов"
        items = ", ".join(user["items"]) if user["items"] else "Нет предметов"
        msg = f"📊 Профиль: {user['name']}\n💰 Баланс: {user['money']} ₽\n🏗 Уровень: {user['level']}\n📜 Последние штрафы:\n{fines}\n🎁 Предметы: {items}"
        await update.message.reply_text(msg, reply_markup=inline_menu())

    elif text == "👥 Игроки банка":
        top = sorted(users.values(), key=lambda x: x["money"], reverse=True)
        msg = "👥 Игроки банка:\n"
        for i, u in enumerate(top[:10], 1):
            msg += f"{i}. {u['name']} — {u['money']} ₽\n"
        await update.message.reply_text(msg, reply_markup=inline_menu())

    elif text == "🔁 Перевести получку":
        await transfer_menu(update, context)

    else:
        await update.message.reply_text("Не понял команду 🤷‍♂️", reply_markup=inline_menu())

# Inline кнопки
async def inline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = get_user(update.effective_user.id, update.effective_user.first_name + " " + (update.effective_user.last_name or ""))

    if query.data == "work":
        now = time.time()
        if now - user["last_work"] < 60:
            msg = "⏳ Смена ещё не закончилась"
        else:
            user["last_work"] = now
            pay_amount = random.randint(800, 1200)
            if "Асфальтовая катка" in user["items"]:
                pay_amount = int(pay_amount * 1.2)
            user["money"] += pay_amount
            msg = f"Получка: {pay_amount} ₽"
        msg += vit_check(user)
        await query.edit_message_text(msg + f"\nБаланс: {user['money']} ₽", reply_markup=inline_menu())

    elif query.data == "shop":
        buttons = [[InlineKeyboardButton(f"{name} — {price} ₽", callback_data=f"buy_{name}")] for name, price in shop_items.items()]
        buttons.append([InlineKeyboardButton("Назад", callback_data="back")])
        markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text("🏗 Магазин: выберите товар", reply_markup=markup)

    elif query.data.startswith("buy_"):
        item_name = query.data[4:]
        cost = shop_items[item_name]
        if user["money"] < cost:
            await query.edit_message_text(f"❌ Недостаточно средств для покупки {item_name}", reply_markup=inline_menu())
        else:
            user["money"] -= cost
            user["items"].append(item_name)
            await query.edit_message_text(f"✅ Куплено {item_name} за {cost} ₽\nБаланс: {user['money']} ₽", reply_markup=inline_menu())

    elif query.data == "deposit":
        gain = int(user["money"] * 0.1)
        user["money"] += gain
        await query.edit_message_text(f"🏦 Депозит +10% = {gain} ₽\nБаланс: {user['money']} ₽", reply_markup=inline_menu())

    elif query.data == "credit":
        user["money"] += 1000
        await query.edit_message_text(f"💳 Кредит +1000 ₽\nБаланс: {user['money']} ₽", reply_markup=inline_menu())

    elif query.data == "transfer":
        await transfer_menu(update, context)

    elif query.data == "back":
        await query.edit_message_text("Вы в меню:", reply_markup=inline_menu())

# Переводы
async def transfer_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if update.callback_query else update.message
    buttons = []
    for uid, u in users.items():
        if uid != update.effective_user.id:
            buttons.append([InlineKeyboardButton(u['name'], callback_data=f"transfer_{uid}")])
    buttons.append([InlineKeyboardButton("Назад", callback_data="back")])
    markup = InlineKeyboardMarkup(buttons)
    if hasattr(query, "edit_message_text"):
        await query.edit_message_text("Выберите игрока для перевода:", reply_markup=markup)
    else:
        await query.reply_text("Выберите игрока для перевода:", reply_markup=markup)

async def transfer_amount_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    receiver_id = int(query.data.split("_")[1])
    context.user_data['transfer_to'] = receiver_id
    await query.edit_message_text("Введите сумму для перевода (например: 500):")

async def transfer_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = get_user(update.effective_user.id, update.effective_user.first_name + " " + (update.effective_user.last_name or ""))
    receiver_id = context.user_data.get('transfer_to')
    if not receiver_id:
        await update.message.reply_text("❌ Ошибка: не выбран получатель")
        return
    try:
        amount = int(update.message.text)
        if sender['money'] < amount:
            await update.message.reply_text("❌ Недостаточно средств")
            return
        receiver = users[receiver_id]
        sender['money'] -= amount
        receiver['money'] += amount
        await update.message.reply_text(f"✅ Вы перевели {amount} ₽ игроку {receiver['name']}")
        try:
            await context.bot.send_message(chat_id=receiver_id, text=f"💸 Вам пришло {amount} ₽ от {sender['name']}!")
        except:
            pass
        context.user_data['transfer_to'] = None
    except ValueError:
        await update.message.reply_text("❌ Введите число")

# /broadcast
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Ты не директор!")
        return
    if not context.args:
        await update.message.reply_text("❌ Использование: /broadcast сообщение")
        return
    msg = " ".join(context.args)
    count = 0
    for uid in users.keys():
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 РАССЫЛКА ОТ ПРОРАБА:\n{msg}")
            count += 1
        except:
            pass
    await update.message.reply_text(f"✅ Сообщение отправлено {count} игрокам")

# Фоновый Виталик
async def vit_worker(app):
    while True:
        for uid, user in users.items():
            msg = vit_check(user)
            if msg:
                try:
                    await app.bot.send_message(chat_id=uid, text=msg + f"\nБаланс: {user['money']} ₽")
                except:
                    pass
        await asyncio.sleep(60)

# Запуск
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_text))
app.add_handler(CallbackQueryHandler(inline_callback))
app.add_handler(CallbackQueryHandler(transfer_amount_prompt, pattern="^transfer_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_amount_received))

async def main():
    asyncio.create_task(vit_worker(app))
    await app.start()
    await app.updater.start_polling()
    await app.idle()

print("Бот КаменскАвтодор запущен")
asyncio.run(main())