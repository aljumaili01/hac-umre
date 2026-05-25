(() => {
  const root = document.documentElement;

  const toastEl = document.getElementById("toast");
  const showToast = (message) => {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.classList.add("is-show");
    window.clearTimeout(showToast._t);
    showToast._t = window.setTimeout(() => toastEl.classList.remove("is-show"), 3200);
  };

  const getStoredTheme = () => window.localStorage.getItem("theme");
  const setTheme = (theme) => {
    root.setAttribute("data-theme", theme);
    window.localStorage.setItem("theme", theme);
    document.querySelectorAll("[data-theme-btn]").forEach((btn) => {
      btn.classList.toggle("is-active", btn.getAttribute("data-theme-btn") === theme);
    });
  };

  const preferred = getStoredTheme();
  if (preferred === "dark" || preferred === "light") {
    setTheme(preferred);
  } else {
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    setTheme(prefersDark ? "dark" : "light");
  }

  document.querySelectorAll("[data-theme-btn]").forEach((btn) => {
    btn.addEventListener("click", () => setTheme(btn.getAttribute("data-theme-btn")));
  });

  const themeToggle = document.getElementById("themeToggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const current = root.getAttribute("data-theme") === "dark" ? "dark" : "light";
      setTheme(current === "dark" ? "light" : "dark");
    });
  }

  const langSelect = document.getElementById("langSelect");
  if (langSelect) {
    langSelect.addEventListener("change", async (e) => {
      const lang = e.target.value;
      try {
        const res = await fetch("/api/set-language", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lang }),
        });
        if (!res.ok) throw new Error("Bad response");
        window.location.reload();
      } catch {
        showToast("Could not switch language.");
      }
    });
  }

  const langMenu = document.getElementById("langMenu");
  const langToggle = document.getElementById("langToggle");
  if (langMenu && langToggle) {
    const setOpen = (open) => {
      langMenu.classList.toggle("is-open", open);
      langToggle.setAttribute("aria-expanded", open ? "true" : "false");
    };

    langToggle.addEventListener("click", () => setOpen(!langMenu.classList.contains("is-open")));

    document.addEventListener("click", (e) => {
      if (!langMenu.classList.contains("is-open")) return;
      const target = e.target;
      if (target instanceof Node && (langMenu.contains(target) || langToggle.contains(target))) return;
      setOpen(false);
    });

    langMenu.addEventListener("click", async (e) => {
      const target = e.target;
      const btn = target && target.closest ? target.closest("[data-lang]") : null;
      if (!btn) return;
      const lang = btn.getAttribute("data-lang");
      if (!lang) return;
      try {
        const res = await fetch("/api/set-language", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lang }),
        });
        if (!res.ok) throw new Error("Bad response");
        window.location.reload();
      } catch {
        showToast("Could not switch language.");
      } finally {
        setOpen(false);
      }
    });
  }

  const nav = document.getElementById("siteNav");
  const navToggle = document.getElementById("navToggle");
  const navClose = document.getElementById("navClose");
  if (nav && navToggle) {
    const setOpen = (open) => {
      nav.classList.toggle("is-open", open);
      navToggle.setAttribute("aria-expanded", open ? "true" : "false");
      document.body.classList.toggle("nav-open", open);
    };

    navToggle.addEventListener("click", () => {
      const isOpen = nav.classList.contains("is-open");
      setOpen(!isOpen);
    });

    if (navClose) navClose.addEventListener("click", () => setOpen(false));

    nav.addEventListener("click", (e) => {
      const link = e.target && e.target.closest ? e.target.closest("a") : null;
      if (link) setOpen(false);
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") setOpen(false);
    });

    const mq = window.matchMedia ? window.matchMedia("(min-width: 981px)") : null;
    const handleMq = () => setOpen(false);
    if (mq) {
      if (mq.addEventListener) mq.addEventListener("change", handleMq);
      else if (mq.addListener) mq.addListener(handleMq);
    }
  }

  const bookingForm = document.getElementById("bookingForm");
  if (bookingForm) {
    bookingForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(bookingForm);
      const payload = {
        package: fd.get("package"),
        full_name: fd.get("full_name"),
        passport_number: fd.get("passport_number"),
        phone: fd.get("phone"),
        people_count: fd.get("people_count"),
      };

      const btn = bookingForm.querySelector("button[type='submit']");
      if (btn) btn.disabled = true;

      try {
        const res = await fetch("/api/bookings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const json = await res.json().catch(() => ({}));
        if (!res.ok || !json.ok) throw new Error(json.error || "Failed");
        bookingForm.reset();
        const msg = (window.__bookingI18n && window.__bookingI18n.ok) || "Booking received.";
        showToast(msg);
      } catch {
        const msg = (window.__bookingI18n && window.__bookingI18n.err) || "Could not submit booking.";
        showToast(msg);
      } finally {
        if (btn) btn.disabled = false;
      }
    });
  }
})();
