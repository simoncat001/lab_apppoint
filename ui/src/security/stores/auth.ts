import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import type { LoginPayload, LoginResponse, User } from '@/security/types/models';
import { login as loginApi, logout as logoutApi } from '@/security/api/endpoints';

const TOKEN_KEY = 'security.token';
const USER_KEY = 'security.user';

// Distinct name + pinia id (`staffAuth`) so this never collides with nemo's
// own auth store even though both are mounted on the same Vue app.
export const useStaffAuthStore = defineStore('staffAuth', () => {
  const token = ref<string | null>(null);
  const user = ref<User | null>(null);
  const isAuthed = computed(() => Boolean(token.value));

  const hydrate = () => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    const storedUser = localStorage.getItem(USER_KEY);
    token.value = storedToken;
    if (storedUser) {
      try {
        user.value = JSON.parse(storedUser) as User;
      } catch {
        user.value = null;
      }
    } else {
      user.value = null;
    }
  };

  const persist = () => {
    if (token.value) {
      localStorage.setItem(TOKEN_KEY, token.value);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
    if (user.value) {
      localStorage.setItem(USER_KEY, JSON.stringify(user.value));
    } else {
      localStorage.removeItem(USER_KEY);
    }
  };

  const login = async (payload: LoginPayload) => {
    const response = (await loginApi(payload)) as LoginResponse;
    token.value = response.token;
    user.value = response.userInfo;
    persist();
  };

  const logout = async () => {
    try {
      await logoutApi();
    } catch {
      // ignore logout errors
    } finally {
      token.value = null;
      user.value = null;
      persist();
    }
  };

  return {
    token,
    user,
    isAuthed,
    hydrate,
    login,
    logout
  };
});
