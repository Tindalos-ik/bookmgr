<!-- 登录页：按入口选择服务端认证 portal，身份始终以真实角色为准。 -->
<script setup lang="ts">
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { BookOpen, ArrowRight } from "lucide-vue-next";
import { errorMessage, ApiError, isRequestCancelled } from "../api/client";
import { useLibraryStore } from "../stores/library";

const store = useLibraryStore();
const route = useRoute();
const router = useRouter();
const account = ref(
  typeof route.query.username === "string" ? route.query.username : "",
);
const password = ref("");
const error = ref("");
const pending = ref(false);

/** 判断当前登录入口是否要求管理员 portal；无参数。 */
function isAdminPortal(): boolean {
  return route.meta.portal === "admin";
}

watch(
  () => route.fullPath,
  () => {
    error.value = "";
    password.value = "";
    account.value =
      typeof route.query.username === "string" ? route.query.username : "";
  },
);

/** 发送凭据与入口 portal，按后端身份进入相应页面。 */
async function submit() {
  if (pending.value) return;
  pending.value = true;
  error.value = "";
  try {
    await store.login(
      account.value.trim(),
      password.value,
      isAdminPortal() ? "admin" : "reader",
    );
    await router.replace(store.isAdmin ? "/manage/books" : "/overview");
  } catch (reason) {
    if (isRequestCancelled(reason)) return;
    error.value =
      reason instanceof ApiError && reason.status === 401
        ? "账号或密码错误，请检查后重试。"
        : reason instanceof ApiError && reason.status === 403
          ? "此账号没有管理员权限，无法从管理员入口登录。"
          : `登录失败：${errorMessage(reason)}`;
  } finally {
    pending.value = false;
  }
}
</script>
<template>
  <main class="login-shell">
    <section class="login-story">
      <div class="brand"><BookOpen :size="30" /><span>青叶书房</span></div>
      <h1>翻开一页，<br />遇见生活的另一种光。</h1>
      <div class="story-art" aria-hidden="true">
        <span></span><span></span><span></span><i></i>
      </div>
    </section>
    <section class="login-form">
      <h2>{{ isAdminPortal() ? "管理员登录" : "用户登录" }}</h2>
      <form @submit.prevent="submit">
        <label class="field">
          账号
          <input
            v-model="account"
            autocomplete="username"
            required
            placeholder="输入账号"
          />
        </label>
        <label class="field">
          密码
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
            placeholder="输入密码"
          />
        </label>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="button login-submit" type="submit" :disabled="pending">
          {{ pending ? "正在登录…" : "进入书房" }}<ArrowRight :size="18" />
        </button>
      </form>
      <nav class="auth-links">
        <RouterLink v-if="isAdminPortal()" to="/login">返回用户登录</RouterLink>
        <template v-else>
          <RouterLink to="/register">注册账号</RouterLink>
          <RouterLink to="/admin/login">管理员登录</RouterLink>
        </template>
      </nav>
    </section>
  </main>
</template>
