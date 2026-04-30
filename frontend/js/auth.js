import { api, clearToken, setToken } from "./api.js";

export function renderAuth(mode = "login") {
  const isLogin = mode === "login";
  return `
    <div class="auth-wrap">
      <div class="auth-box">
        <div class="auth-title">Ad-Synth AI</div>
        <div class="auth-subtitle">${isLogin ? "Sign in to your account" : "Create a new account"}</div>
        <form id="auth-form">
          <div class="form-group">
            <label>Email</label>
            <input type="email" id="auth-email" placeholder="you@company.com" required />
          </div>
          <div class="form-group">
            <label>Password</label>
            <input type="password" id="auth-password" placeholder="••••••••" required />
          </div>
          <div class="error-msg" id="auth-error"></div>
          <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;margin-top:8px">
            ${isLogin ? "Sign in" : "Create account"}
          </button>
        </form>
        <div class="auth-switch">
          ${isLogin
            ? `Don't have an account? <a id="auth-toggle">Register</a>`
            : `Already have an account? <a id="auth-toggle">Sign in</a>`
          }
        </div>
      </div>
    </div>
  `;
}

export function bindAuth(mode = "login") {
  document.getElementById("auth-toggle")?.addEventListener("click", () => {
    window.location.hash = mode === "login" ? "#register" : "#login";
  });

  document.getElementById("auth-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("auth-email").value.trim();
    const password = document.getElementById("auth-password").value;
    const errEl = document.getElementById("auth-error");
    errEl.textContent = "";
    const btn = e.target.querySelector("button[type=submit]");
    btn.disabled = true;

    try {
      if (mode === "register") {
        await api.register(email, password);
      }
      const { access_token } = await api.login(email, password);
      setToken(access_token);
      localStorage.setItem("user_email", email);
      window.location.hash = "#campaigns";
    } catch (err) {
      errEl.textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  });
}

export function logout() {
  clearToken();
  window.location.hash = "#login";
}
