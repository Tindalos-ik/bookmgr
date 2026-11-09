<!-- 登录页：账号密码由后端认证，演示快捷入口也提交真实凭据。 -->
<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { BookOpen, ArrowRight } from "lucide-vue-next";
import { errorMessage, ApiError, isRequestCancelled } from "../api/client";
import { useLibraryStore } from "../stores/library";
const store = useLibraryStore(),
  router = useRouter();
const account = ref(""),
  password = ref(""),
  error = ref(""),
  pending = ref(false);
/** 发送表单凭据到后端并显示认证或网络错误。 */
async function submit() {
  if (pending.value) return;
  pending.value = true;
  error.value = "";
  try {
    await store.login(account.value.trim(), password.value);
    await router.push("/overview");
  } catch (reason) {
    if (isRequestCancelled(reason)) return;
    error.value =
      reason instanceof ApiError && reason.status === 401
        ? "账号或密码错误，请检查后重试。"
        : `登录失败：${errorMessage(reason)}`;
  } finally {
    pending.value = false;
  }
}
/** 将 accountName 指定的 reader/admin 演示账号填入表单并通过真实接口认证。 */
async function enterDemo(accountName: "reader" | "admin") {
  account.value = accountName;
  password.value = accountName === "reader" ? "reader123" : "admin123";
  await submit();
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
      <h2>登录青叶书房</h2>
      <form @submit.prevent="submit">
        <label class="field"
          >账号<input
            v-model="account"
            autocomplete="username"
            required
            placeholder="请输入演示账号" /></label
        ><label class="field"
          >密码<input
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
            placeholder="请输入演示密码"
        /></label>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="button login-submit" type="submit" :disabled="pending">
          {{ pending ? "正在登录…" : "进入书房" }}<ArrowRight :size="18" />
        </button>
      </form>
      <div class="demo-box">
        <strong>公开演示账号</strong>
        <p>读者：reader / reader123<br />管理员：admin / admin123</p>
        <div class="demo-actions">
          <button
            class="button secondary"
            :disabled="pending"
            @click="enterDemo('reader')"
          >
            读者快捷登录</button
          ><button
            class="button secondary"
            :disabled="pending"
            @click="enterDemo('admin')"
          >
            管理员快捷登录
          </button>
        </div>
        <p class="demo-safety">演示账号公开，请勿填写敏感资料。</p>
      </div>
    </section>
  </main>
</template>
