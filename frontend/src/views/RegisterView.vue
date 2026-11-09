<!-- 注册页面：创建读者账号，不自动登录。 -->
<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError, errorMessage, isRequestCancelled } from "../api/client";
import { useLibraryStore } from "../stores/library";

const store = useLibraryStore();
const router = useRouter();
const username = ref("");
const password = ref("");
const confirmation = ref("");
const error = ref("");
const pending = ref(false);

/** 校验账号与密码后提交真实注册请求，成功返回登录页。 */
async function submit() {
  if (pending.value) return;
  const name = username.value.trim();
  const usernameLength = [...name].length;
  if (usernameLength < 3 || usernameLength > 60) {
    error.value = "用户名需为3至60个字符。";
    return;
  }
  const passwordLength = [...password.value].length;
  if (passwordLength < 8 || passwordLength > 128 || !password.value.trim()) {
    error.value = "密码需为8至128个字符，且不能全为空白。";
    return;
  }
  if (password.value !== confirmation.value) {
    error.value = "两次输入的密码不一致。";
    return;
  }

  pending.value = true;
  error.value = "";
  try {
    await store.register(name, password.value);
    store.notify("注册成功，请登录");
    await router.replace({ path: "/login", query: { username: name } });
  } catch (reason) {
    if (isRequestCancelled(reason)) return;
    error.value =
      reason instanceof ApiError && reason.status === 409
        ? "用户名已被使用，请更换后重试。"
        : `注册失败：${errorMessage(reason)}`;
  } finally {
    pending.value = false;
  }
}
</script>
<template>
  <main class="auth-shell">
    <section class="auth-card">
      <h1>注册账号</h1>
      <form @submit.prevent="submit">
        <label class="field">
          用户名
          <input
            v-model="username"
            autocomplete="username"
            minlength="3"
            required
          />
        </label>
        <label class="field">
          密码
          <input
            v-model="password"
            type="password"
            autocomplete="new-password"
            minlength="8"
            required
          />
        </label>
        <label class="field">
          确认密码
          <input
            v-model="confirmation"
            type="password"
            autocomplete="new-password"
            required
          />
        </label>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="button auth-submit" type="submit" :disabled="pending">
          {{ pending ? "正在注册…" : "注册" }}
        </button>
      </form>
      <RouterLink to="/login">返回用户登录</RouterLink>
    </section>
  </main>
</template>
