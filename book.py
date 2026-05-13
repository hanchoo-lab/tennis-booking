"""
Tennis Court Auto-Booking Script
Runs inside GitHub Actions at midnight WIB (00:00 UTC+7).
No local server or open browser needed.
"""

import json, os, time
from datetime import datetime, date, timedelta
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# ── Config ────────────────────────────────────────────────────────────────
BOOKING_EMAIL = os.environ.get("BOOKING_EMAIL", "hanchoo@gmail.com")
SCHEDULE_FILE = Path(__file__).parent / "schedule.json"

COURT_URLS = {
    1: "https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ2y-UCm6xL7xhvVWiKOxqZJa6vyaUHbi50X4bGfSDwTmcQDyTUwi_fqvi-2vYH18hkcIUJ3wcNm?gv=true",
    2: "https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ0khaHwW9_DvWBFmCUhpHe-khaGLq7zajAeXNPbBppNFwGMPzSzl_oI5fdBe9iZI2jKtJcYDUMs?gv=true",
    3: "https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ0iQu6Dovr-zBRgHz84quFU_cU5yBF92sPqrjwORGKt7XSOls9zMKtESFV4rllRTDQnPO1j665j?gv=true",
}

MONTHS = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]

# ── Helpers ───────────────────────────────────────────────────────────────
def fmt_display(hour: int, minute: int = 0) -> str:
    ampm = "am" if hour < 12 else "pm"
    h    = 12 if hour == 0 else (hour - 12 if hour > 12 else hour)
    return f"{h}:{'00' if minute == 0 else str(minute).zfill(2)}{ampm}"

def react_set(driver, el, value: str):
    driver.execute_script("""
        var el=arguments[0],v=arguments[1];
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')
              .set.call(el,v);
        el.dispatchEvent(new Event('input',  {bubbles:true}));
        el.dispatchEvent(new Event('change', {bubbles:true}));
    """, el, value)

def find_input_by_label(driver, label_text: str):
    try:
        for lbl in driver.find_elements(By.TAG_NAME, "label"):
            if label_text.lower() not in (lbl.text or "").lower():
                continue
            fid = lbl.get_attribute("for")
            if fid:
                try: return driver.find_element(By.ID, fid)
                except: pass
            try: return lbl.find_element(By.CSS_SELECTOR, "input,textarea")
            except: pass
            result = driver.execute_script("""
                var l=arguments[0],s=l.nextElementSibling;
                while(s){var i=s.matches('input,textarea')?s:s.querySelector('input,textarea');
                         if(i)return i;s=s.nextElementSibling;}
                var p=l.parentElement;
                if(p){var ps=p.nextElementSibling;
                      while(ps){var i2=ps.matches('input,textarea')?ps:ps.querySelector('input,textarea');
                                if(i2)return i2;ps=ps.nextElementSibling;}}
                return null;
            """, lbl)
            if result: return result
    except: pass
    return None

# ── Core booking ──────────────────────────────────────────────────────────
def book_court(court_num: int, date_str: str, time_str: str) -> str:
    year, month, day = map(int, date_str.split("-"))
    hour, minute     = map(int, time_str.split(":"))
    display_time     = fmt_display(hour, minute)
    target_month     = MONTHS[month - 1]

    print(f"\n>>> Booking Court {court_num} | {date_str} | {display_time}")

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1400,900")
    # Force WIB locale/timezone in Chrome
    opts.add_argument("--lang=id-ID")

    driver = webdriver.Chrome(options=opts)
    wait   = WebDriverWait(driver, 15)

    try:
        print("  Loading booking page...")
        driver.get(COURT_URLS[court_num])
        time.sleep(5)

        # ── Timezone override via CDP ──────────────────────────────────────
        for attempt in range(3):
            try:
                driver.execute_cdp_cmd("Emulation.setTimezoneOverride",
                                       {"timezoneId": "Asia/Jakarta"})
                print("  CDP timezone set to Asia/Jakarta")
                break
            except Exception as e:
                print(f"  CDP timezone attempt {attempt+1} failed: {e}")
                time.sleep(1)
        driver.refresh()
        time.sleep(5)

        # ── Full diagnostic dump ───────────────────────────────────────────
        tz_detected = driver.execute_script(
            "return Intl.DateTimeFormat().resolvedOptions().timeZone;"
        )
        print(f"  Browser timezone: {tz_detected}")

        print("  === ALL interactive elements (button / role=button) ===")
        all_items = driver.execute_script("""
            var out = [];
            var nodes = document.querySelectorAll('button,[role="button"]');
            for (var b of nodes) {
                var lbl = b.getAttribute('aria-label') || '';
                var txt = b.textContent.trim().replace(/\\s+/g,' ');
                var dis = b.disabled || b.getAttribute('aria-disabled') === 'true';
                out.push({ lbl: lbl.substring(0,100),
                           txt: txt.substring(0,60),
                           dis: dis });
            }
            return out;
        """)
        for item in all_items:
            flag = " [DISABLED]" if item['dis'] else ""
            lbl  = item['lbl']
            txt  = item['txt']
            print(f"    aria={lbl!r}  txt={txt!r}{flag}")
        print(f"  (Total interactive: {len(all_items)})")

        # ── Step 1: Navigate to the correct week ──────────────────────────
        # The week view starts from today and shows 7 consecutive days.
        # We need to advance one "next week" per 7 days between today and target.
        target_dt    = date(year, month, day)
        today_dt     = date.today()
        days_ahead   = (target_dt - today_dt).days
        weeks_ahead  = max(0, days_ahead // 7)
        print(f"  Today={today_dt}, Target={target_dt}, days_ahead={days_ahead}, weeks_ahead={weeks_ahead}")

        for w in range(weeks_ahead):
            clicked = driver.execute_script("""
                var sel = 'button,[role="button"]';
                // Prefer "next week" (aria contains 'next', not 'month')
                for (var b of document.querySelectorAll(sel)) {
                    var lbl = (b.getAttribute('aria-label') || '').toLowerCase();
                    var dis = b.disabled || b.getAttribute('aria-disabled') === 'true';
                    if (lbl.includes('next') && !lbl.includes('month') && !dis) {
                        b.click(); return 'lbl:' + lbl;
                    }
                }
                // Fallback: › or > text
                for (var b of document.querySelectorAll(sel)) {
                    var t = b.textContent.trim();
                    var dis = b.disabled || b.getAttribute('aria-disabled') === 'true';
                    if ((t === '›' || t === '>') && !dis) { b.click(); return 'arrow'; }
                }
                return null;
            """)
            if not clicked:
                raise RuntimeError(f"Cannot advance to week {w+1}/{weeks_ahead}")
            print(f"  Week advance {w+1}/{weeks_ahead}: {clicked}")
            time.sleep(1.2)

        time.sleep(1.5)

        # ── Step 2: Find and click the time slot ──────────────────────────
        # Time slot buttons typically have an aria-label that includes the date.
        # E.g. "6:00 AM – 7:00 AM, Friday, May 15, 2026"
        # We search for a button whose aria-label contains BOTH the date fragment
        # AND the time fragment.  Several format variants are tried in order.
        target_day_num = str(day)
        searches = [
            # (label_fragment_1, label_fragment_2)  — both must appear in aria-label
            (target_month, f"{target_day_num},"),        # "May 15,"
            (target_month, f"{target_day_num} "),        # "May 15 "
            (f"{target_month} {target_day_num}", None),  # "May 15"
            (display_time, None),                        # just the time — last resort
        ]

        print(f"  Searching for time slot: {display_time} on {target_month} {target_day_num}, {year}")

        # Print all time-like buttons for diagnosis
        time_buttons = driver.execute_script("""
            var out = [];
            for (var b of document.querySelectorAll('button,[role="button"]')) {
                var lbl = b.getAttribute('aria-label') || '';
                var txt = b.textContent.trim();
                var dis = b.disabled || b.getAttribute('aria-disabled') === 'true';
                if (/[0-9]+:[0-9]+(\\s)?(am|pm|AM|PM)/i.test(lbl) ||
                    /[0-9]+:[0-9]+(\\s)?(am|pm|AM|PM)/i.test(txt)) {
                    out.push({ lbl: lbl.substring(0,120), txt: txt.substring(0,60), dis: dis });
                }
            }
            return out;
        """)
        print(f"  Time-related buttons found: {len(time_buttons)}")
        for tb in time_buttons[:20]:
            flag = " [DISABLED]" if tb['dis'] else ""
            print(f"    aria={tb['lbl']!r}  txt={tb['txt']!r}{flag}")

        found_time = False
        for attempt in range(20):
            # Try aria-label search with date+time fragments
            for frag1, frag2 in searches:
                result = driver.execute_script("""
                    var frag1 = arguments[0];
                    var frag2 = arguments[1];
                    var t     = arguments[2].toLowerCase();
                    var sel   = 'button,[role="button"]';
                    for (var b of document.querySelectorAll(sel)) {
                        var lbl = b.getAttribute('aria-label') || '';
                        var lblL = lbl.toLowerCase();
                        var txt  = b.textContent.trim().toLowerCase();
                        var dis  = b.disabled || b.getAttribute('aria-disabled') === 'true';
                        if (dis) continue;
                        // Must contain time fragment
                        var hasTime = lblL.includes(t) || txt === t;
                        if (!hasTime) continue;
                        // Must contain date fragment(s)
                        var hasDate = lbl.includes(frag1) || lblL.includes(frag1.toLowerCase());
                        if (frag2) hasDate = hasDate && (lbl.includes(frag2) || lblL.includes(frag2.toLowerCase()));
                        if (hasDate) { b.click(); return 'date+time:' + lbl.substring(0,60); }
                    }
                    return null;
                """, frag1, frag2 or "", display_time)
                if result:
                    found_time = True
                    print(f"  Clicked time slot ({result})")
                    break
            if found_time:
                break
            time.sleep(0.8)

        if not found_time:
            # Last resort: click the first button whose text exactly matches the time
            result = driver.execute_script("""
                var t = arguments[0].toLowerCase();
                for (var b of document.querySelectorAll('button,[role="button"]')) {
                    var dis = b.disabled || b.getAttribute('aria-disabled') === 'true';
                    if (!dis && b.textContent.trim().toLowerCase() === t) {
                        b.click(); return 'text-only';
                    }
                }
                return null;
            """, display_time)
            if result:
                found_time = True
                print(f"  Clicked time slot by text only ({result}) — WARNING: may be wrong day")
            else:
                driver.save_screenshot("screenshot_debug.png")
                visible = [f"{tb['lbl'] or tb['txt']}" for tb in time_buttons]
                raise RuntimeError(
                    f'"{display_time}" not found for {target_month} {day}. '
                    f"Visible time slots: {visible[:10]}"
                )

        time.sleep(2.5)

        # ── Step 3: Fill the booking form ─────────────────────────────────
        wait.until(lambda d: len(d.find_elements(
            By.CSS_SELECTOR, 'input[type="text"],input:not([type])')) >= 2)
        time.sleep(0.5)

        all_inp = driver.execute_script(
            "return Array.from(document.querySelectorAll('input[type=\"text\"],input:not([type])'))"
            ".filter(e=>e.offsetParent);"
        )

        fn    = find_input_by_label(driver, "first name")  or (all_inp[0] if len(all_inp)>0 else None)
        ln    = find_input_by_label(driver, "last name")   or (all_inp[1] if len(all_inp)>1 else None)
        email = find_input_by_label(driver, "email")       or (all_inp[2] if len(all_inp)>2 else None)
        jis   = find_input_by_label(driver, "JIS")         or (all_inp[3] if len(all_inp)>3 else None)

        if fn:    react_set(driver, fn,    "Tennis")
        if ln:    react_set(driver, ln,    "Singles")
        if email: react_set(driver, email, BOOKING_EMAIL)
        if jis:   react_set(driver, jis,   "C")
        print(f"  Form filled (fn={bool(fn)}, ln={bool(ln)}, email={bool(email)}, jis={bool(jis)})")
        time.sleep(1.2)

        # ── Step 4: Click Book ────────────────────────────────────────────
        booked = driver.execute_script("""
            for (var b of document.querySelectorAll('button,[role="button"]')) {
                var dis = b.disabled || b.getAttribute('aria-disabled') === 'true';
                if (b.textContent.trim() === 'Book' && !dis) { b.click(); return true; }
            }
            return false;
        """)
        if not booked:
            driver.save_screenshot("screenshot_debug.png")
            raise RuntimeError("Book button not found or disabled")

        print("  Clicked Book!")
        time.sleep(6)

        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        ok   = any(w in body for w in ("confirmed","booked","scheduled","thank"))
        print(f"  Confirmation on page: {ok}")
        if not ok:
            print(f"  Page body snippet: {body[:400]}")
            driver.save_screenshot("screenshot_debug.png")

        return f"Court {court_num} booked for {date_str} at {display_time}. Check your email."

    except Exception:
        try: driver.save_screenshot("screenshot_debug.png")
        except: pass
        raise

    finally:
        time.sleep(1)
        try: driver.quit()
        except: pass

# ── Main: process due bookings ────────────────────────────────────────────
def main():
    with open(SCHEDULE_FILE) as f:
        bookings = json.load(f)

    today   = date.today()
    changed = False
    ran     = 0

    for b in bookings:
        if b["status"] not in ("pending", "queued"):
            continue
        run_at = datetime.fromisoformat(b["run_at"]).date()
        if run_at > today:
            print(f"  Skipping Court {b['court']} {b['date']} — scheduled for {run_at}")
            continue

        ran += 1
        print(f"\n=== Running: Court {b['court']} | {b['date']} | {b['time']} ===")
        try:
            msg = book_court(b["court"], b["date"], b["time"])
            b["status"]  = "success"
            b["message"] = msg
        except Exception as e:
            b["status"]  = "failed"
            b["message"] = str(e)
            print(f"  ERROR: {e}")
        b["completed_at"] = datetime.now().isoformat()
        changed = True

    if ran == 0:
        print("No bookings due today.")

    if changed:
        with open(SCHEDULE_FILE, "w") as f:
            json.dump(bookings, f, indent=2)
        print(f"\nUpdated {SCHEDULE_FILE}")

if __name__ == "__main__":
    main()
