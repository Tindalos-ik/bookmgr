<!-- 密码修改页面：服务端确认后清除已撤销的会话。 -->
<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { errorMessage, isRequestCancelled } from "../api/client";
import { useLibraryStore } from "../stores/library";

const store = useLibraryStore();
const router = useRouter();
const oldPassword = ref("");
const newPassword = ref("");
const confirmation = ref("");
const error = ref("");
const pending = ref(false);

/** 提交当前账户密码变更，成功后不再使用旧令牌。 */
async function submit() {
  if (pending.value) return;
  const oldLength = [...oldPassword.value].length;
  if (oldLength < 1 || oldLength > 128) {
    error.value = "旧密码需为1至128个字符。";
    return;
  }
  const newLength = [...newPassword.value].length;
  if (newLength < 8 || newLength > 128 || !newPassword.value.trim()) {
    error.value = "新密码需为8至128个字符，且不能全为空白。";
    return;
  }
  if (oldPassword.value === newPassword.value) {
    error.value = "新密码不能与旧密码相同。";
    return;
  }
  if (newPassword.value !== confirmation.value) {
    error.value = "两次输入的新密码不一致。";
    return;
  }

  pending.value = true;
  error.value = "";
  try {
    await store.changePassword(oldPassword.value, newPassword.value);
    oldPassword.value = "";
    newPassword.value = "";
    confirmation.value = "";
    await router.replace("/login");
  } catch (reason) {
    if (isRequestCancelled(reason)) return;
    error.value = `修改密码失败：${errorMessage(reason)}`;
  } finally {
    pending.value = false;
  }
}
</script>
<template>
  <main class="auth-card password-card">
    <h1>修改密码</h1>
    <form @submit.prevent="submit">
      <label class="field">
        旧密码
        <input
          v-model="oldPassword"
          type="password"
          autocomplete="current-password"
          required
        />
      </label>
      <label class="field">
        新密码
        <input
          v-model="newPassword"
          type="password"
          autocomplete="new-password"
          minlength="8"
          required
        />
      </label>
      <label class="field">
        确认新密码
        <input
          v-model="confirmation"
          type="password"
          autocomplete="new-password"
          required
        />
      </label>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <button class="button auth-submit" type="submit" :disabled="pending">
        {{ pending ? "正在修改…" : "确认修改" }}
      </button>
    </form>
  </main>
</template>
