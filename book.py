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

def wib_to_page_time(hour: int, minute: int, page_tz_offset_min: int):
    """
    Convert a WIB (UTC+7) time to whatever timezone the booking page shows.

    page_tz_offset_min  = JS getTimezoneOffset() value
                        = minutes WEST of UTC  (positive for Americas)
                        e.g. EDT = 240, MST/PDT = 420, UTC = 0, WIB = -420

    Returns (page_hour, page_minute, day_delta)
    day_delta = -1 means the slot appears on the calendar day BEFORE
    the WIB target date (common for Americas timezones).
    """
    wib_min  = hour * 60 + minute
    utc_min  = wib_min - 7 * 60          # WIB → UTC  (subtract +7)
    page_min = utc_min - page_tz_offset_min  # UTC → page local

    day_delta = 0
    while page_min < 0:
        page_min  += 24 * 60
        day_delta -= 1
    while page_min >= 24 * 60:
        page_min  -= 24 * 60
        day_delta += 1

    return page_min // 60, page_min % 60, day_delta

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
    display_time_wib = fmt_display(hour, minute)   # e.g. "6:00am" (WIB)
    target_month     = MONTHS[month - 1]

    print(f"\n>>> Booking Court {court_num} | {date_str} | {display_time_wib} WIB")

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1400,900")

    driver = webdriver.Chrome(options=opts)
    wait   = WebDriverWait(driver, 15)

    try:
        print("  Loading booking page...")
        driver.get(COURT_URLS[court_num])
        time.sleep(5)

        # ── Detect page timezone and convert our WIB time ─────────────────
        page_tz_offset = driver.execute_script("return new Date().getTimezoneOffset();")
        page_tz_name   = driver.execute_script(
            "return Intl.DateTimeFormat().resolvedOptions().timeZone;"
        )
        print(f"  Page timezone: {page_tz_name} (offset {page_tz_offset} min west of UTC)")

        ph, pm, day_delta = wib_to_page_time(hour, minute, page_tz_offset)
        display_time_page = fmt_display(ph, pm)
        page_date         = date(year, month, day) + timedelta(days=day_delta)
        page_day_num      = str(page_date.day)
        page_month_name   = MONTHS[page_date.month - 1]

        print(f"  WIB {display_time_wib} on {date_str}  →  "
              f"page shows '{display_time_page}' on {page_date} "
              f"(day_delta={day_delta})")

        # ── Dump all time-related buttons for diagnosis ───────────────────
        def dump_time_buttons(label=""):
            btns = driver.execute_script("""
                var out = [];
                for (var b of document.querySelectorAll('button,[role="button"]')) {
                    var lbl = b.getAttribute('aria-label') || '';
                    var txt = b.textContent.trim().replace(/\s+/g,' ');
                    var dis = b.disabled || b.getAttribute('aria-disabled') === 'true';
                    if (/\d+:\d+\s*(am|pm)/i.test(lbl+txt))
                        out.push({lbl:lbl.substring(0,120), txt:txt.substring(0,60), dis:dis});
                }
                return out;
            """)
            print(f"  Time buttons{' '+label if label else ''} ({len(btns)}):")
            for b in btns:
                flag = " [DIS]" if b['dis'] else ""
                print(f"    txt={b['txt']!r}  aria={b['lbl']!r}{flag}")
            return btns

        dump_time_buttons("on load")

        # ── Step 1: Navigate to the week containing page_date ─────────────
        today_dt    = date.today()
        days_ahead  = (page_date - today_dt).days
        weeks_ahead = max(0, days_ahead // 7)
        print(f"  Navigating {weeks_ahead} week(s) forward (today={today_dt}, page_date={page_date})")

        for w in range(weeks_ahead):
            clicked = driver.execute_script("""
                var sel = 'button,[role="button"]';
                for (var b of document.querySelectorAll(sel)) {
                    var lbl = (b.getAttribute('aria-label') || '').toLowerCase();
                    var dis = b.disabled || b.getAttribute('aria-disabled') === 'true';
                    if (lbl.includes('next') && !lbl.includes('month') && !dis) {
                        b.click(); return 'lbl:' + lbl;
                    }
                }
                for (var b of document.querySelectorAll(sel)) {
                    var t = b.textContent.trim();
                    if ((t === '›' || t === '>') && !b.disabled) { b.click(); return 'arrow'; }
                }
                return null;
            """)
            if not clicked:
                raise RuntimeError(f"Cannot advance to week {w+1}/{weeks_ahead}")
            print(f"  Week {w+1}/{weeks_ahead}: {clicked}")
            time.sleep(1.2)

        if weeks_ahead > 0:
            time.sleep(1.5)
            dump_time_buttons("after navigation")

        # ── Step 2: Click the time slot ───────────────────────────────────
        # Search strategy (in order):
        #   A. aria-label contains BOTH page_date info AND time
        #   B. aria-label contains time only
        #   C. button text matches exactly
        print(f"  Clicking: '{display_time_page}' on {page_month_name} {page_day_num} "
              f"(= {display_time_wib} WIB on {date_str})")

        found_time = False
        for attempt in range(20):
            result = driver.execute_script("""
                var dMonth  = arguments[0];   // "May"
                var dDay    = arguments[1];   // "14"
                var dYear   = arguments[2];   // "2026"
                var dTime   = arguments[3];   // "7:00pm"
                var sel = 'button,[role="button"]';

                function ok(b) {
                    return !b.disabled && b.getAttribute('aria-disabled') !== 'true';
                }
                function hasTime(s) {
                    s = s.toLowerCase().replace(/\s/g,'');
                    return s.includes(dTime.toLowerCase().replace(/\s/g,''));
                }
                function hasDate(s) {
                    var sl = s.toLowerCase();
                    return (sl.includes(dMonth.toLowerCase()) && sl.includes(dDay)) ||
                           sl.includes(dDay + ',' + dYear) ||
                           sl.includes(dDay + ' ' + dYear);
                }

                // Pass A: date + time in aria-label
                for (var b of document.querySelectorAll(sel)) {
                    if (!ok(b)) continue;
                    var lbl = b.getAttribute('aria-label') || '';
                    if (hasDate(lbl) && hasTime(lbl)) {
                        b.click(); return 'A:' + lbl.substring(0,80);
                    }
                }
                // Pass B: time in aria-label only
                for (var b of document.querySelectorAll(sel)) {
                    if (!ok(b)) continue;
                    var lbl = b.getAttribute('aria-label') || '';
                    if (hasTime(lbl) && lbl.length > 2) {
                        b.click(); return 'B:' + lbl.substring(0,80);
                    }
                }
                // Pass C: exact text match
                for (var b of document.querySelectorAll(sel)) {
                    if (!ok(b)) continue;
                    if (b.textContent.trim().toLowerCase() ===
                        dTime.toLowerCase()) {
                        b.click(); return 'C:text';
                    }
                }
                return null;
            """, page_month_name, page_day_num, str(page_date.year), display_time_page)

            if result:
                found_time = True
                print(f"  Clicked time slot (attempt {attempt+1}): {result}")
                break
            time.sleep(0.8)

        if not found_time:
            tb = dump_time_buttons("at failure")
            visible = [b['txt'] or b['lbl'] for b in tb]
            driver.save_screenshot("screenshot_debug.png")
            raise RuntimeError(
                f'"{display_time_page}" ({display_time_wib} WIB) not found '
                f"on {page_month_name} {page_day_num}. "
                f"Visible slots: {visible}"
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
        print(f"  Form filled (fn={bool(fn)}, ln={bool(ln)}, "
              f"email={bool(email)}, jis={bool(jis)})")
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

        return (f"Court {court_num} booked for {date_str} at {display_time_wib} WIB. "
                "Check your email.")

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
