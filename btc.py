import requests
import time
import os
import numpy as np
from datetime import datetime

# ===== ألوان ANSI محسنة =====
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    BLACK = "\033[90m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"
    RESET = "\033[0m"
    
    # خلفيات
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

# ===== لوحة أكثر احترافية =====
LOGO = f"""
{Colors.BG_BLACK}{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════════════════════════════════════╗
║{Colors.BG_BLUE}                                                                                      ║
║{Colors.BG_BLUE}   ███████╗ █████╗ ██╗███╗   ██╗     ███╗   ██╗███████╗██████╗  ██████╗               ║
║{Colors.BG_BLUE}   ██╔════╝██╔══██╗██║████╗  ██║     ████╗  ██║██╔════╝██╔══██╗██╔════╝               ║
║{Colors.BG_BLUE}   █████╗  ███████║██║██╔██╗ ██║     ██╔██╗ ██║█████╗  ██████╔╝██║  ███╗              ║
║{Colors.BG_BLUE}   ██╔══╝  ██╔══██║██║██║╚██╗██║     ██║╚██╗██║██╔══╝  ██╔══██╗██║   ██║              ║
║{Colors.BG_BLUE}   ██║     ██║  ██║██║██║ ╚████║     ██║ ╚████║███████╗██║  ██║╚██████╔╝              ║
║{Colors.BG_BLUE}   ╚═╝     ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝     ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝               ║
║{Colors.BG_BLUE}                                                                                      ║
║{Colors.BG_BLUE}                          🦅 نظام عين النسر - Eagle Eye System                        ║
║{Colors.BG_BLUE}                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════╝
{Colors.RESET}
"""

class EagleEyeOneShot:
    def __init__(self):
        # REST endpoints
        self.ticker_url     = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
        self.order_book_url = "https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=50"
        self.trade_url      = "https://api.binance.com/api/v3/trades?symbol=BTCUSDT&limit=100"

        # حالة النظام
        self.init_done = False
        self.prev_price = 0.0

        # تراكم حقيقي من الصفقات الجديدة
        self.cum_buys  = 0.0
        self.cum_sells = 0.0

        # آخر trade id
        self.last_trade_id = None

        # إعدادات الذكاء
        self.VOLUME_DIFF_THRESHOLD = 10.0  # عتبة الفرق في الكمية (10 BTC)
        self.MIN_COOLDOWN_SEC    = 20
        self.last_signal_time    = 0
        self.current_signal      = "⚪ انتظار"
        self.current_future_txt  = "السوق هادئ، ننتظر تفاوت في الكمية"
        self.current_color       = Colors.YELLOW
        self.last_net_msg        = ""

        # عدادات ثانية
        self.last_second_ts      = 0
        self.sec_buy_volume      = 0.0
        self.sec_sell_volume     = 0.0

        # عدد المحاولات عند الفشل
        self.retry_count = 0
        self.max_retries = 3

        # أداء النظام
        self.start_time = time.time()
        self.request_count = 0

    # أدوات مساعدة
    def clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")

    def now_ts(self):
        return int(time.time())

    # جلب البيانات مع معالجة الأخطاء
    def fetch_data(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            self.retry_count = 0  # إعادة تعيين عدد المحاولات عند النجاح
            self.request_count += 1
            return response.json()
        except requests.exceptions.RequestException as e:
            self.retry_count += 1
            if self.retry_count > self.max_retries:
                print(f"{Colors.RED}⛔ فشل في الاتصال بعد {self.max_retries} محاولات. تأكد من اتصالك بالإنترنت.{Colors.RESET}")
                return None
            print(f"{Colors.YELLOW}⚠️ خطأ في الاتصال: {e}. إعادة المحاولة ({self.retry_count}/{self.max_retries})...{Colors.RESET}")
            time.sleep(2)
            return self.fetch_data(url)  # إعادة المحاولة

    def get_ticker(self):
        return self.fetch_data(self.ticker_url)

    def get_order_book(self):
        return self.fetch_data(self.order_book_url)

    def get_recent_trades(self):
        return self.fetch_data(self.trade_url)

    # تهيئة أولية
    def init_from_ticker(self, ticker):
        self.prev_price = float(ticker.get("lastPrice", "0") or 0)
        self.init_done = True

    # دعم/مقاومة مبسط
    def support_resistance_from_book(self, ob):
        try:
            bids = np.array([[float(p), float(q)] for p, q in ob.get("bids", [])], dtype=float)
            asks = np.array([[float(p), float(q)] for p, q in ob.get("asks", [])], dtype=float)
            support = float(bids[np.argmax(bids[:,1])][0]) if bids.size else 0.0
            resistance = float(asks[np.argmax(asks[:,1])][0]) if asks.size else 0.0
            return support, resistance
        except Exception:
            return 0.0, 0.0

    # معالجة الصفقات الجديدة
    def consume_new_trades(self, trades):
        if not trades:
            return 0.0, 0.0, None, None

        trades_sorted = sorted(trades, key=lambda t: t["id"])

        if self.last_trade_id is None:
            self.last_trade_id = trades_sorted[-1]["id"]
            return 0.0, 0.0, None, None

        buy_volume = 0.0
        sell_volume = 0.0
        first_new_id = None
        last_new_id = None

        for t in trades_sorted:
            tid = t["id"]
            if tid > self.last_trade_id:
                qty = float(t["qty"])
                if t["isBuyerMaker"]:
                    sell_volume += qty
                else:
                    buy_volume += qty
                if first_new_id is None:
                    first_new_id = tid
                last_new_id = tid

        if last_new_id is not None:
            self.last_trade_id = last_new_id

        # تراكم شامل
        self.cum_buys  += buy_volume
        self.cum_sells += sell_volume

        # عدادات ثانية
        now = self.now_ts()
        if now != self.last_second_ts:
            self.sec_buy_volume  = buy_volume
            self.sec_sell_volume = sell_volume
            self.last_second_ts = now
        else:
            self.sec_buy_volume  += buy_volume
            self.sec_sell_volume += sell_volume

        return buy_volume, sell_volume, first_new_id, last_new_id

    # منطق الإشارة - يعتمد على الفرق التراكمي في الكمية
    def maybe_fire_signal(self, price, support, resistance):
        now = self.now_ts()
        in_cooldown = (now - self.last_signal_time) < self.MIN_COOLDOWN_SEC

        # حساب الفرق التراكمي في الكمية
        cumulative_difference = abs(self.cum_buys - self.cum_sells)
        cumulative_imbalance = self.cum_buys - self.cum_sells

        # إشارة شراء: عندما يكون الفرق التراكمي لصالح الشراء
        if cumulative_difference >= self.VOLUME_DIFF_THRESHOLD and cumulative_imbalance > 0:
            if not in_cooldown or self.current_signal != "🟢 شراء 100%":
                target = resistance if resistance > 0 else price * 1.01
                self.current_signal = "🟢 شراء 100%"
                self.current_future_txt = f"{Colors.GREEN}تفوق تراكمي في كمية الشراء ({self.cum_buys:.2f} BTC شراء vs {self.cum_sells:.2f} BTC بيع) → هدف أول ~ {target:,.2f}${Colors.RESET}"
                self.current_color = Colors.GREEN
                self.last_signal_time = now
                self.last_net_msg = f"+{self.cum_buys:.2f} BTC شراء، -{self.cum_sells:.2f} BTC بيع (فرق تراكمي: +{cumulative_imbalance:.2f} BTC)"
            return

        # إشارة بيع: عندما يكون الفرق التراكمي لصالح البيع
        if cumulative_difference >= self.VOLUME_DIFF_THRESHOLD and cumulative_imbalance < 0:
            if not in_cooldown or self.current_signal != "🔴 بيع 100%":
                target = support if support > 0 else price * 0.99
                self.current_signal = "🔴 بيع 100%"
                self.current_future_txt = f"{Colors.RED}تفوق تراكمي في كمية البيع ({self.cum_sells:.2f} BTC بيع vs {self.cum_buys:.2f} BTC شراء) → هدف أول ~ {target:,.2f}${Colors.RESET}"
                self.current_color = Colors.RED
                self.last_signal_time = now
                self.last_net_msg = f"-{self.cum_sells:.2f} BTC بيع، +{self.cum_buys:.2f} BTC شراء (فرق تراكمي: {cumulative_imbalance:.2f} BTC)"
            return

        if not in_cooldown and self.current_signal.startswith("⚪") == False:
            self.current_signal = "⚪ انتظار"
            self.current_future_txt = f"{Colors.CYAN}لا يوجد تفاوت واضح في الكمية. ننتظر فرقًا يبلغ {self.VOLUME_DIFF_THRESHOLD}+ BTC.{Colors.RESET}"
            self.current_color = Colors.YELLOW
            self.last_net_msg = ""

    # عرض الشاشة بمظهر أكثر احترافية
    def render(self, price, support, resistance, ticker):
        self.clear_screen()
        print(LOGO)
        
        # معلومات الوقت وأداء النظام
        uptime = time.time() - self.start_time
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        print(f"{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD} ⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
              f"🔄 الطلبات: {self.request_count} | "
              f"⏱ تشغيل: {int(hours)}:{int(minutes):02d}:{int(seconds):02d} {Colors.RESET}")
        
        # السعر الحالي مع مؤشر التغير
        price_change = ""
        if self.prev_price > 0:
            change = price - self.prev_price
            change_percent = (change / self.prev_price) * 100
            change_color = Colors.GREEN if change >= 0 else Colors.RED
            change_symbol = "▲" if change >= 0 else "▼"
            price_change = f" ({change_color}{change_symbol} {abs(change):.2f} [{abs(change_percent):.2f}%]{Colors.RESET})"
        
        print(f"\n{Colors.BOLD}{Colors.UNDERLINE}السوق الحالي:{Colors.RESET}")
        print(f"{Colors.BOLD}💰 السعر: {self.current_color}${price:,.2f}{price_change}{Colors.RESET}")
        
        if support > 0 or resistance > 0:
            print(f"📊 الدعم: {Colors.BLUE}${support:,.2f}{Colors.RESET} | المقاومة: {Colors.MAGENTA}${resistance:,.2f}{Colors.RESET}")
        
        # إشارة التداول
        print(f"\n{Colors.BOLD}{Colors.UNDERLINE}إشارة التداول:{Colors.RESET}")
        print(f"🎯 {Colors.BOLD}{self.current_signal}{Colors.RESET}")
        print(f"📈 {self.current_future_txt}")
        
        if self.last_net_msg:
            print(f"⚡ {self.last_net_msg}")
        
        # إحصائيات الحجم
        print(f"\n{Colors.BOLD}{Colors.UNDERLINE}إحصائيات الحجم:{Colors.RESET}")
        print(f"⏱️ الحجم/ثانية: {Colors.GREEN}شراء {self.sec_buy_volume:.4f} BTC{Colors.RESET} | "
              f"{Colors.RED}بيع {self.sec_sell_volume:.4f} BTC{Colors.RESET} | "
              f"الفرق: {Colors.CYAN}{self.sec_buy_volume - self.sec_sell_volume:+.4f} BTC{Colors.RESET}")
        
        print(f"📊 التراكم: {Colors.GREEN}شراء {self.cum_buys:.4f} BTC{Colors.RESET} | "
              f"{Colors.RED}بيع {self.cum_sells:.4f} BTC{Colors.RESET} | "
              f"الفرق: {Colors.CYAN}{self.cum_buys - self.cum_sells:+.4f} BTC{Colors.RESET}")
        
        # معلومات النظام
        print(f"\n{Colors.BOLD}{Colors.UNDERLINE}إعدادات النظام:{Colors.RESET}")
        print(f"⚙️  عتبة التفاوت: {self.VOLUME_DIFF_THRESHOLD} BTC | "
              f"وقت التبريد: {self.MIN_COOLDOWN_SEC} ثانية | "
              f"الحالة: {'✅ متصل' if self.retry_count == 0 else '⚠️ إعادة محاولة ' + str(self.retry_count)}")
        
        # تذييل
        print(f"\n{Colors.BLACK}{Colors.BG_WHITE} اضغط Ctrl+C للإيقاف {Colors.RESET}")

    # المراقبة الرئيسية
    def monitor(self):
        try:
            while True:
                try:
                    ticker = self.get_ticker()
                    if ticker is None:
                        continue

                    order_book = self.get_order_book()
                    if order_book is None:
                        continue

                    trades = self.get_recent_trades()
                    if trades is None:
                        continue

                    price = float(ticker.get("lastPrice", "0") or 0)

                    if not self.init_done:
                        self.init_from_ticker(ticker)

                    support, resistance = self.support_resistance_from_book(order_book)

                    buy_volume, sell_volume, first_id, last_id = self.consume_new_trades(trades)

                    self.maybe_fire_signal(price, support, resistance)

                    self.render(price, support, resistance, ticker)

                    self.prev_price = price
                    time.sleep(1)
                except Exception as e:
                    print(f"{Colors.RED}⚠️ خطأ غير متوقع: {e}. استمرار المحاولة...{Colors.RESET}")
                    time.sleep(2)
        except KeyboardInterrupt:
            print(f"\n{Colors.RED}⛔ تم إيقاف النظام.{Colors.RESET}")


if __name__ == "__main__":
    app = EagleEyeOneShot()
    app.monitor()
