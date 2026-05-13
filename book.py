"""
Tennis Court Auto-Booking Script
Runs inside GitHub Actions at midnight WIB (00:00 UTC+7).
No local server or open browser needed.
"""

import json, os, time
from datetime import datetime, date
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
    target_label     = f"{target_month} {day}, {year}"

    print(f"\n>>> Booking Court {court_num} | {date_str} | {display_time}")

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
        time.sleep(4)

<<<<<<< HEAD
        # ── Step 1: Navigate to the correct date ──────────────────────────
        print(f"  Looking for date button: '{target_label}'")
        clicked_date = False

        for attempt in range(16):
            # Try clicking the target date by aria-label
            result = driver.execute_script(
                "var exp=arguments[0];"
                "for(var b of document.querySelectorAll('button')){"
                "  var lbl=b.getAttribute('aria-label')||'';"
                "  if(lbl.indexOf(exp)!==-1&&!b.disabled){b.click();return 'ok';}"
                "}"
                "return null;",
                target_label
            )
            if result:
                clicked_date = True
                print(f"  Clicked date (attempt {attempt+1})")
                break

            # Not found yet – log and advance the calendar
            visible_dates = driver.execute_script(
                "var out=[];"
                "for(var b of document.querySelectorAll('button')){"
                "  var lbl=b.getAttribute('aria-label')||'';"
                "  if(lbl.match(/[A-Z][a-z]+ [0-9]+, [0-9]{4}/)){out.push(lbl);}"
                "}"
                "return out.slice(0,5);"
            )
            print(f"  Attempt {attempt+1}: not found. Sample dates on page: {visible_dates}")

            # Click next (prefer week-level next, fall back to any next)
            advanced = driver.execute_script(
                "var btns=document.querySelectorAll('button');"
                "for(var b of btns){"
                "  var lbl=(b.getAttribute('aria-label')||'').toLowerCase();"
                "  if(lbl.indexOf('next')!==-1&&lbl.indexOf('month')===-1&&!b.disabled){b.click();return 'week-next';}"
                "}"
                "for(var b of btns){"
                "  var t=b.textContent.trim();"
                "  if((t==='›'||t==='>')&&!b.disabled){b.click();return 'arrow-next';}"
                "}"
                "for(var b of btns){"
                "  var lbl=(b.getAttribute('aria-label')||'').toLowerCase();"
                "  if(lbl.indexOf('next')!==-1&&!b.disabled){b.click();return 'any-next';}"
                "}"
                "return null;"
            )
            if not advanced:
                print("  ERROR: No Next button found — dumping all button labels:")
                all_btns = driver.execute_script(
                    "return Array.from(document.querySelectorAll('button')).map(b=>(b.getAttribute('aria-label')||b.textContent.trim()).substring(0,60));"
                )
                for btn in all_btns:
                    print(f"    [{btn}]")
                driver.save_screenshot("screenshot_debug.png")
                raise RuntimeError("Cannot advance calendar — no Next button found")

            print(f"  Advanced calendar ({advanced})")
            time.sleep(0.9)

        if not clicked_date:
            driver.save_screenshot("screenshot_debug.png")
            raise RuntimeError(
                f"Date '{target_label}' not found after 16 navigation attempts. "
                "It may be outside the 72-hour booking window."
            )

        time.sleep(2.5)

        # ── Step 2: Click the time slot ───────────────────────────────────
        print(f"  Looking for time slot: '{display_time}'")
        found_time = False

        for attempt in range(15):
            result = driver.execute_script(
                "var t=arguments[0].toLowerCase();"
                "for(var b of document.querySelectorAll('button')){"
                "  if(b.textContent.trim().toLowerCase()===t&&!b.disabled){b.click();return true;}"
                "}"
                "return false;",
                display_time
=======
        # Navigate to correct week using week-view arrows
        from datetime import date as _d, timedelta as _td
        target_dt   = _d(year, month, day)
        today_dt    = _d.today()
        weeks_ahead = max(0, ((target_dt - _td(days=target_dt.weekday())) -
                              (today_dt  - _td(days=today_dt.weekday()))).days // 7)
        print(f"  Advancing {weeks_ahead} week(s)...")
        for _ in range(weeks_ahead):
            driver.execute_script("""
                for(var b of document.querySelectorAll('button')){
                    var l=(b.getAttribute('aria-label')||'').toLowerCase();
                    if(l.includes('next')&&!l.includes('month')&&!b.disabled){b.click();return;}
                }
                for(var b of document.querySelectorAll('button')){
                    var t=b.textContent.trim();
                    if((t==='\u203a'||t==='>')&&!b.disabled){b.click();return;}
                }
            """)
            time.sleep(1.0)

        # Click date by aria-label only (no guessing by number)
        result = driver.execute_script("""
            var exp=arguments[1]+' '+arguments[0]+', '+arguments[2];
            for(var b of document.querySelectorAll('button')){
                if((b.getAttribute('aria-label')||'').includes(exp)&&!b.disabled){b.click();return true;}
            }
            return null;
        """, day, target_month, year)
        if not result:
            raise RuntimeError(f"{target_month} {day} not clickable — may not be in the booking window yet")
        print(f"  Clicked {target_month} {day}")
        time.sleep(2.5)

        # Click time slot
        found = False
        for _ in range(12):
            found = driver.execute_script("""
                var t=arguments[0];
                for(var b of document.querySelectorAll('button')){
                    if(b.textContent.trim().toLowerCase()===t.toLowerCase()&&!b.disabled){
                        b.click();return true;
                    }
                }return false;
            """, display_time)
            if found: break
            time.sleep(1.0)
        if not found:
            driver.save_screenshot("screenshot_debug.png")
            raise RuntimeError(
                f'"{display_time}" not available — slot may be outside the 72-hour window or already booked.'
>>>>>>> 91ae41bab75df89da1ace446c184c943b0d9096c
            )
            if result:
                found_time = True
                break
            time.sleep(0.8)

        if not found_time:
            # Log all visible time buttons for debugging
            visible_times = driver.execute_script(
                "var out=[];"
                "for(var b of document.querySelectorAll('button')){"
                "  var t=b.textContent.trim();"
                "  if(t.match(/^[0-9]+:[0-9]+(am|pm)$/i)){out.push(t);}"
                "}"
                "return out;"
            )
            print(f"  Available time slots on page: {visible_times}")
            driver.save_screenshot("screenshot_debug.png")
            raise RuntimeError(
                f'"{display_time}" not available — '
                f"visible slots: {visible_times}. "
                "Slot may be outside the 72-hour window or already booked."
            )

        print(f"  Clicked time: {display_time}")
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
        booked = driver.execute_script(
            "for(var b of document.querySelectorAll('button')){"
            "  if(b.textContent.trim()==='Book'&&!b.disabled){b.click();return true;}"
            "}"
            "return false;"
        )
        if not booked:
            driver.save_screenshot("screenshot_debug.png")
            raise RuntimeError("Book button not found or disabled")

        print("  Clicked Book!")
        time.sleep(6)

        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        ok   = any(w in body for w in ("confirmed","booked","scheduled","thank"))
        print(f"  Confirmation on page: {ok}")
        if not ok:
            print(f"  Page body snippet: {body[:300]}")
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
