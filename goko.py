import sqlite3
import datetime
import telebot
from telebot import types

TOKEN = "8557118906:AAEOTeEdq-hv0d60MzCkgwonsUXymKZ9du8"
FOUNDER_ID = 7731769678
OWNER_USERNAME = "Denktinee"

# Zorunlu Kanallar
CHANNEL_1 = "@pubgHack92"
CHANNEL_2 = "@yago_frewl"

bot = telebot.TeleBot(TOKEN)
temp_data = {}

# ---------------- DATABASE SETUP ----------------
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            points INTEGER DEFAULT 0,
            last_bonus TEXT,
            is_banned INTEGER DEFAULT 0,
            referrer_id INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (FOUNDER_ID,))
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price INTEGER,
            stock_code TEXT DEFAULT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_name TEXT,
            price INTEGER,
            status TEXT DEFAULT 'BEKLIYOR',
            delivered_code TEXT DEFAULT NULL,
            date TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promos (
            code TEXT PRIMARY KEY,
            points INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

def is_admin(user_id):
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM admins WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res is not None or user_id == FOUNDER_ID

# Kanal Kontrol Fonksiyonu
def check_channels(user_id):
    if user_id == FOUNDER_ID:
        return True
    try:
        status1 = bot.get_chat_member(CHANNEL_1, user_id).status
        status2 = bot.get_chat_member(CHANNEL_2, user_id).status
        unwanted = ['left', 'kicked']
        if status1 not in unwanted and status2 not in unwanted:
            return True
    except:
        pass
    return False

# ---------------- HANDLERS ----------------
@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    
    c.execute("SELECT is_banned FROM users WHERE user_id=?", (user.id,))
    banned = c.fetchone()
    if banned and banned[0] == 1 and user.id != FOUNDER_ID:
        bot.reply_to(message, "⛔ Üzgünüz, bu botu kullanımınız engellenmiştir.")
        conn.close()
        return

    conn.close()

    if not check_channels(user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 1. Kanalı Takip Et", url=f"https://t.me/{CHANNEL_1.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("📢 2. Kanalı Takip Et", url=f"https://t.me/{CHANNEL_2.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("✅ Kontrol Et / Başlat", callback_data="check_sub"))
        bot.send_message(message.chat.id, f"⚠️ Botu kullanabilmek için öncelikle aşağıdaki kanallarımızı takip etmelisin:\n\n1️⃣ {CHANNEL_1}\n2️⃣ {CHANNEL_2}\n\nTakip ettikten sonra **Kontrol Et** butonuna bas.", reply_markup=markup)
        return

    register_user_and_show_main(message)

def register_user_and_show_main(message_or_call, is_call=False):
    user = message_or_call.from_user
    chat_id = message_or_call.message.chat.id if is_call else message_or_call.chat.id
    
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    
    text = message_or_call.text if not is_call else ""
    args = text.split()
    ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != user.id else None
    
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)", 
                  (user.id, user.username, ref_id))
        if ref_id:
            c.execute("UPDATE users SET points = points + 5 WHERE user_id=?", (ref_id,))
            try:
                bot.send_message(ref_id, "🎉 Referansınızla yeni bir üye katıldı! +5 Puan kazandınız.")
            except: pass
        conn.commit()
    conn.close()

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 Profilim & Bakiyem", callback_data="user_profile"),
               types.InlineKeyboardButton("🏪 Market & Ürünler 🛒", callback_data="user_market"))
    markup.add(types.InlineKeyboardButton("📜 Geçmiş Siparişlerim", callback_data="user_orders"))
    markup.add(types.InlineKeyboardButton("🎁 Günlük Bonus (24 Saatte Bir)", callback_data="user_bonus"))
    markup.add(types.InlineKeyboardButton("🎟️ Promo Kod Kullan", callback_data="use_promo"))
    markup.add(types.InlineKeyboardButton("👥 Referans Sistemi", callback_data="user_ref"))
    
    buy_url = f"https://t.me/{OWNER_USERNAME}?text=MERHABA%20PUAN%20SATIN%20ALMAK%20ISTIYORUM"
    markup.add(types.InlineKeyboardButton("💎 Puan Satın Al", url=buy_url))
    markup.add(types.InlineKeyboardButton("📢 Reklam Yaptır", url=f"https://t.me/{OWNER_USERNAME}"))
    markup.add(types.InlineKeyboardButton("💬 İletişim & Şikayet Et", callback_data="user_complaint"))
    
    if is_admin(user.id):
        markup.add(types.InlineKeyboardButton("⚙️ Admin Paneli", callback_data="admin_panel"))

    welcome_text = f"👋 Merhaba {user.first_name}!\n\nBot Marketimize Hoş Geldiniz:"
    if is_call:
        bot.edit_message_text(welcome_text, chat_id, message_or_call.message.message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    data = call.data
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()

    if data == "check_sub":
        if check_channels(user_id):
            bot.answer_callback_query(call.id, "✅ Kanallar onaylandı! Bot açılıyor...", show_alert=True)
            register_user_and_show_main(call, is_call=True)
        else:
            bot.answer_callback_query(call.id, "❌ Henüz kanallara abone olmamışsın!", show_alert=True)

    elif data == "user_profile":
        c.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
        pts = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE referrer_id=?", (user_id,))
        ref_count = c.fetchone()[0]
        
        msg = f"👤 **KULLANICI PROFİLİ**\n\n🆔 **ID:** `{user_id}`\n💰 **Bakiye:** {pts} Puan\n👥 **Davet Edilen Üye:** {ref_count} Kişi"
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

    elif data == "user_orders":
        c.execute("SELECT product_name, price, status, delivered_code, date FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 5", (user_id,))
        orders = c.fetchall()
        if not orders:
            bot.answer_callback_query(call.id, "Henüz hiç siparişiniz yok.")
            return
        
        msg = "📜 **SON 5 SİPARİŞİNİZ:**\n\n"
        for o in orders:
            code_txt = f"\n🔑 **Teslim Edilen Kod:** `{o[3]}`" if o[3] else ""
            msg += f"🛍️ **Ürün:** {o[0]} ({o[1]} Puan)\n📌 **Durum:** {o[2]}{code_txt}\n📅 **Tarih:** {o[4]}\n---\n"
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

    elif data == "user_bonus":
        c.execute("SELECT last_bonus, points FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        now = datetime.datetime.now()
        
        can_claim = False
        if not row[0]:
            can_claim = True
        else:
            last_date = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
            if (now - last_date).total_seconds() >= 86400:
                can_claim = True

        if can_claim:
            c.execute("UPDATE users SET points = points + 10, last_bonus = ? WHERE user_id=?", 
                      (now.strftime("%Y-%m-%d %H:%M:%S"), user_id))
            conn.commit()
            bot.answer_callback_query(call.id, "🎉 +10 Puan eklendi!", show_alert=True)
            bot.edit_message_text("🎉 Tebrikler! Günlük bonus olarak 10 Puan hesabınıza eklendi.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "⏳ 24 saat geçmesi gerekiyor!", show_alert=True)

    elif data == "use_promo":
        bot.edit_message_text("🎟️ Lütfen geçerli **Promo Kodunu** yazıp gönderin:", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, process_promo_code)

    elif data == "user_ref":
        c.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
        pts = c.fetchone()[0]
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        bot.edit_message_text(f"👥 **Referans Sistemi**\n\nMevcut Puanınız: {pts}\nDavet Linkiniz:\n{ref_link}\n\nHer davet ettiğiniz kişi için +5 Puan kazanırsınız!", call.message.chat.id, call.message.message_id)

    elif data == "user_market":
        c.execute("SELECT id, name, price, stock_code FROM products")
        prods = c.fetchall()
        if not prods:
            bot.edit_message_text("🛒 Henüz stokta ürün bulunmamaktadır.", call.message.chat.id, call.message.message_id)
        else:
            markup = types.InlineKeyboardMarkup()
            for p in prods:
                auto_tag = "⚡ Otomatik" if p[3] else "⏳ Onaylı"
                markup.add(types.InlineKeyboardButton(f"{p[1]} - 💰 {p[2]} Puan [{auto_tag}]", callback_data=f"buy_{p[0]}"))
            bot.edit_message_text("🏪 **Market & Ürün Listesi:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "user_complaint":
        bot.edit_message_text("💬 Lütfen şikayet veya iletişim mesajınızı doğrudan yazıp gönderin, adminlere iletilecektir.", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, save_complaint)

    # --- ADMIN PANEL ---
    elif data == "admin_panel" and is_admin(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Puan Ekle", callback_data="a_pt_add"),
                   types.InlineKeyboardButton("➖ Puan Sil", callback_data="a_pt_sub"))
        markup.add(types.InlineKeyboardButton("📦 Ürün Ekle", callback_data="a_pr_add"),
                   types.InlineKeyboardButton("🗑️ Ürün Sil", callback_data="a_pr_del"))
        markup.add(types.InlineKeyboardButton("🎟️ Promo Kod Oluştur", callback_data="a_promo_add"))
        markup.add(types.InlineKeyboardButton("👑 Yönetici Ekle", callback_data="a_ad_add"),
                   types.InlineKeyboardButton("🚫 Yönetici Sil", callback_data="a_ad_del"))
        markup.add(types.InlineKeyboardButton("🔨 Kullanıcı Banla", callback_data="a_ban"),
                   types.InlineKeyboardButton("📢 Duyuru At", callback_data="a_broadcast"))
        markup.add(types.InlineKeyboardButton("🛒 Siparişler", callback_data="a_orders"),
                   types.InlineKeyboardButton("📩 Şikayetler", callback_data="a_complaints"))
        bot.edit_message_text("⚙️ **PRO ADMIN KONTROL PANELI**", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "a_promo_add" and is_admin(user_id):
        msg = bot.send_message(user_id, "🎟️ Oluşturmak istediğiniz **Promo Kodunu** yazın (Örn: `BEDAVA50`):")
        bot.register_next_step_handler(msg, admin_promo_name)

    elif data == "a_pt_add" and is_admin(user_id):
        msg = bot.send_message(user_id, "➕ Puan eklenecek **Kullanıcı ID**'sini yazın:")
        bot.register_next_step_handler(msg, admin_point_add_id)
    elif data == "a_pt_sub" and is_admin(user_id):
        msg = bot.send_message(user_id, "➖ Puan silinecek **Kullanıcı ID**'sini yazın:")
        bot.register_next_step_handler(msg, admin_point_sub_id)
    elif data == "a_pr_add" and is_admin(user_id):
        msg = bot.send_message(user_id, "📦 Eklenecek ürünün adını yazın:")
        bot.register_next_step_handler(msg, admin_prod_add_name)
    elif data == "a_pr_del" and is_admin(user_id):
        c.execute("SELECT id, name, price FROM products")
        prods = c.fetchall()
        if not prods:
            bot.answer_callback_query(call.id, "Silinecek ürün yok.")
            return
        markup = types.InlineKeyboardMarkup()
        for p in prods:
            markup.add(types.InlineKeyboardButton(f"Sil: {p[1]} ({p[2]} Puan)", callback_data=f"delprod_{p[0]}"))
        bot.edit_message_text("🗑️ Silmek istediğiniz ürünü seçin:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif data.startswith("delprod_") and is_admin(user_id):
        pid = int(data.split("_")[1])
        c.execute("DELETE FROM products WHERE id=?", (pid,))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ Ürün silindi!", show_alert=True)
        bot.edit_message_text("✅ Ürün başarıyla silindi.", call.message.chat.id, call.message.message_id)
    elif data == "a_ad_add" and is_admin(user_id):
        msg = bot.send_message(user_id, "👑 Yönetici yapılacak yeni **Kullanıcı ID**'sini yazın:")
        bot.register_next_step_handler(msg, admin_add_admin)
    elif data == "a_ad_del" and is_admin(user_id):
        msg = bot.send_message(user_id, "🚫 Yöneticiliği kaldırılacak **Kullanıcı ID**'sini yazın:")
        bot.register_next_step_handler(msg, admin_del_admin)
    elif data == "a_ban" and is_admin(user_id):
        msg = bot.send_message(user_id, "🔨 Banlanacak veya banı kaldırılacak **Kullanıcı ID**'sini yazın:")
        bot.register_next_step_handler(msg, admin_toggle_ban)
    elif data == "a_broadcast" and is_admin(user_id):
        msg = bot.send_message(user_id, "📢 Tüm kullanıcılara gönderilecek mesajı yazın:")
        bot.register_next_step_handler(msg, admin_broadcast_exec)

    elif data == "a_orders" and is_admin(user_id):
        c.execute("SELECT id, user_id, product_name, price FROM orders WHERE status='BEKLIYOR'")
        orders = c.fetchall()
        if not orders:
            bot.answer_callback_query(call.id, "Bekleyen manuel sipariş yok.")
            return
        for o in orders:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Onayla", callback_data=f"ord_app_{o[0]}"),
                       types.InlineKeyboardButton("❌ Reddet & İade", callback_data=f"ord_rej_{o[0]}"))
            bot.send_message(user_id, f"📦 Sipariş #{o[0]}\n👤 Kullanıcı: `{o[1]}`\n🛍️ Ürün: {o[2]} ({o[3]} Puan)", reply_markup=markup, parse_mode="Markdown")

    elif data == "a_complaints" and is_admin(user_id):
        c.execute("SELECT user_id, message FROM complaints")
        comps = c.fetchall()
        if not comps:
            bot.answer_callback_query(call.id, "Şikayet yok.")
            return
        msg = "📩 **Gelen Şikayetler / Destek Mesajları:**\n\n"
        for comp in comps:
            msg += f"👤 `{comp[0]}`: {comp[1]}\n---\n"
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

    elif data.startswith("ord_app_") and is_admin(user_id):
        ord_id = int(data.split("_")[2])
        c.execute("SELECT user_id, product_name FROM orders WHERE id=?", (ord_id,))
        o_data = c.fetchone()
        c.execute("UPDATE orders SET status='ONAYLANDI' WHERE id=?", (ord_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "Onaylandı.")
        try: bot.send_message(o_data[0], f"🎉 `{o_data[1]}` siparişiniz onaylandı!")
        except: pass

    elif data.startswith("ord_rej_") and is_admin(user_id):
        ord_id = int(data.split("_")[2])
        c.execute("SELECT user_id, product_name, price FROM orders WHERE id=?", (ord_id,))
        o_data = c.fetchone()
        c.execute("UPDATE orders SET status='REDDEDILDI' WHERE id=?", (ord_id,))
        c.execute("UPDATE users SET points = points + ? WHERE user_id=?", (o_data[2], o_data[0]))
        conn.commit()
        bot.answer_callback_query(call.id, "Reddedildi ve puan iade edildi.")
        try: bot.send_message(o_data[0], f"⚠️ Siparişiniz reddedildi, {o_data[2]} puanınız iade edildi.")
        except: pass

    elif data.startswith("buy_"):
        pid = int(data.split("_")[1])
        c.execute("SELECT name, price, stock_code FROM products WHERE id=?", (pid,))
        prod = c.fetchone()
        c.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
        u_pts = c.fetchone()[0]

        if u_pts < prod[1]:
            bot.answer_callback_query(call.id, f"❌ Yetersiz Puan! Gereken: {prod[1]}", show_alert=True)
        else:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute("UPDATE users SET points = points - ? WHERE user_id=?", (prod[1], user_id))
            
            if prod[2]:
                c.execute("INSERT INTO orders (user_id, product_name, price, status, delivered_code, date) VALUES (?, ?, ?, 'ONAYLANDI', ?, ?)", 
                          (user_id, prod[0], prod[1], prod[2], now_str))
                conn.commit()
                bot.answer_callback_query(call.id, "⚡ Otomatik teslimat gerçekleşti!", show_alert=True)
                bot.send_message(user_id, f"🎉 `{prod[0]}` ürününü başarıyla satın aldınız!\n\n🔑 **Teslimat Kodunuz:**\n`{prod[2]}`", parse_mode="Markdown")
            else:
                c.execute("INSERT INTO orders (user_id, product_name, price, status, date) VALUES (?, ?, ?, 'BEKLIYOR', ?)", 
                          (user_id, prod[0], prod[1], now_str))
                conn.commit()
                bot.answer_callback_query(call.id, "✅ Sipariş alındı! Yönetici onaylayacak.", show_alert=True)

    conn.close()

# --- PROMO VE ADIMLI FONKSİYONLAR ---
def process_promo_code(message):
    code = message.text.strip().upper()
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("SELECT points FROM promos WHERE code=?", (code,))
    row = c.fetchone()
    
    if not row:
        bot.reply_to(message, "❌ Geçersiz veya süresi dolmuş promosyon kodu!")
        conn.close()
        return
    
    pts = row[0]
    c.execute("DELETE FROM promos WHERE code=?", (code,))
    c.execute("UPDATE users SET points = points + ? WHERE user_id=?", (pts, message.from_user.id))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"🎉 Tebrikler! Promo kod başarıyla uygulandı ve hesabınıza **{pts} Puan** eklendi!", parse_mode="Markdown")

def admin_promo_name(message):
    temp_data[message.from_user.id] = {"promo_code": message.text.strip().upper()}
    msg = bot.reply_to(message, "🎟️ Bu promo kod kaç **Puan** verecek? (Sayı olarak yazın):")
    bot.register_next_step_handler(msg, admin_promo_points)

def admin_promo_points(message):
    if not message.text.isdigit():
        bot.reply_to(message, "❌ Geçersiz miktar.")
        return
    pts = int(message.text)
    code = temp_data[message.from_user.id]["promo_code"]
    
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO promos (code, points) VALUES (?, ?)", (code, pts))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"✅ Başarılı! `{code}` kodlu promosyon ({pts} Puan) oluşturuldu.", parse_mode="Markdown")

def admin_broadcast_exec(message):
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()

    count = 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 **DUYURU:**\n\n{message.text}", parse_mode="Markdown")
            count += 1
        except: pass
    bot.reply_to(message, f"✅ Duyuru toplam {count} kullanıcıya ulaştırıldı.")

def admin_point_add_id(message):
    if not message.text.isdigit():
        bot.reply_to(message, "❌ Geçersiz ID.")
        return
    temp_data[message.from_user.id] = {"target_user": int(message.text)}
    msg = bot.reply_to(message, "Eklenecek **Puan Miktarını** yazın:")
    bot.register_next_step_handler(msg, admin_point_add_exec)

def admin_point_add_exec(message):
    if not message.text.isdigit():
        bot.reply_to(message, "❌ Geçersiz miktar.")
        return
    amt = int(message.text)
    uid = temp_data[message.from_user.id]["target_user"]
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("UPDATE users SET points = points + ? WHERE user_id=?", (amt, uid))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ Başarıyla `{uid}` ID'li kullanıcıya {amt} puan eklendi.", parse_mode="Markdown")

def admin_point_sub_id(message):
    if not message.text.isdigit():
        bot.reply_to(message, "❌ Geçersiz ID.")
        return
    temp_data[message.from_user.id] = {"target_user": int(message.text)}
    msg = bot.reply_to(message, "Silinecek **Puan Miktarını** yazın:")
    bot.register_next_step_handler(msg, admin_point_sub_exec)

def admin_point_sub_exec(message):
    if not message.text.isdigit():
        bot.reply_to(message, "❌ Geçersiz miktar.")
        return
    amt = int(message.text)
    uid = temp_data[message.from_user.id]["target_user"]
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("UPDATE users SET points = MAX(0, points - ?) WHERE user_id=?", (amt, uid))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ `{uid}` ID'li kullanıcıdan {amt} puan silindi.", parse_mode="Markdown")

def admin_prod_add_name(message):
    temp_data[message.from_user.id] = {"p_name": message.text}
    msg = bot.reply_to(message, "Ürünün **Puan Fiyatını** yazın:")
    bot.register_next_step_handler(msg, admin_prod_add_price)

def admin_prod_add_price(message):
    if not message.text.isdigit():
        bot.reply_to(message, "❌ Geçersiz fiyat.")
        return
    temp_data[message.from_user.id]["p_price"] = int(message.text)
    msg = bot.reply_to(message, "🔑 Otomatik teslim edilecek **Kod/Hesap Bilgisini** yazın (Eğer otomatik değilse sadece `YOK` yazın):")
    bot.register_next_step_handler(msg, admin_prod_add_code)

def admin_prod_add_code(message):
    code = None if message.text.upper() == "YOK" else message.text
    name = temp_data[message.from_user.id]["p_name"]
    price = temp_data[message.from_user.id]["p_price"]
    
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("INSERT INTO products (name, price, stock_code) VALUES (?, ?, ?)", (name, price, code))
    conn.commit()
    conn.close()
    
    auto_txt = "⚡ (Otomatik)" if code else "⏳ (Manuel)"
    bot.reply_to(message, f"✅ '{name}' ürünü {price} puan fiyatıyla markete eklendi! {auto_txt}")

def admin_add_admin(message):
    if not message.text.isdigit():
        bot.reply_to(message, "❌ Geçersiz ID.")
        return
    uid = int(message.text)
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (uid,))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"👑 `{uid}` ID'li kullanıcı başarıyla yönetici yapıldı.", parse_mode="Markdown")

def admin_del_admin(message):
    if not message.text.isdigit():
        bot.reply_to(message, "❌ Geçersiz ID.")
        return
    uid = int(message.text)
    if uid == FOUNDER_ID:
        bot.reply_to(message, "❌ Kurucu yönetici silinemez!")
        return
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"🚫 `{uid}` ID'li kullanıcının yöneticiliği kaldırıldı.", parse_mode="Markdown")

def admin_toggle_ban(message):
    if not message.text.isdigit():
        bot.reply_to(message, "❌ Geçersiz ID.")
        return
    uid = int(message.text)
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("SELECT is_banned FROM users WHERE user_id=?", (uid,))
    row = c.fetchone()
    if not row:
        bot.reply_to(message, "❌ Bu kullanıcı veritabanında bulunamadı.")
        conn.close()
        return
    
    new_status = 0 if row[0] == 1 else 1
    c.execute("UPDATE users SET is_banned = ? WHERE user_id=?", (new_status, uid))
    conn.commit()
    conn.close()
    
    status_txt = "BANLANDI 🔨" if new_status == 1 else "BANI KALDIRILDI ✅"
    bot.reply_to(message, f"ℹ️ `{uid}` ID'li kullanıcı durumu: {status_txt}", parse_mode="Markdown")

def save_complaint(message):
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("INSERT INTO complaints (user_id, message) VALUES (?, ?)", (message.from_user.id, message.text))
    conn.commit()
    conn.close()
    bot.reply_to(message, "✅ Şikayetiniz/mesajınız yöneticilere başarıyla iletildi.")

print("Bot tam sürüm olarak başlatıldı...")
bot.infinity_polling()
