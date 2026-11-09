<!-- 应用入口：身份验证失败可重试，未确认身份时不展示业务页面。 -->
<script setup lang="ts">
import { watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useLibraryStore } from "./stores/library";
import { X } from "lucide-vue-next";
const store = useLibraryStore();
const router = useRouter();
const route = useRoute();
/** 重试真实身份及收藏恢复，无参数；成功后根据权限返回可见页面。 */
async function retrySession() {
  await store.retryInitialize();
  if (store.restoreError) return;
  if (!store.session) await router.replace("/login");
  else if (route.path === "/login" || (route.meta.admin && !store.isAdmin)) {
    await router.replace("/overview");
  }
}
watch(
  [() => store.session, () => store.initialized],
  ([session, initialized]) => {
    if (
      initialized &&
      !store.restoreError &&
      !session &&
      route.path !== "/login"
    ) {
      void router.replace("/login");
    }
  },
);
</script>
<template>
  <main v-if="store.restoreError || store.restoring" class="session-recovery">
    <h1>{{ store.restoring ? "正在验证登录状态" : "暂时无法恢复书房" }}</h1>
    <p role="status">
      {{
        store.restoring ? "正在连接后端并读取当前账号资料…" : store.restoreError
      }}
    </p>
    <p v-if="!store.restoring">连接恢复后可重试，无需重新登录。</p>
    <button class="button" :disabled="store.restoring" @click="retrySession">
      {{ store.restoring ? "正在验证…" : "重试登录验证" }}
    </button>
  </main>
  <RouterView v-else />
  <div class="notice" aria-live="polite" aria-atomic="true">
    <template v-if="store.notice">
      <span>{{ store.notice }}</span>
      <button aria-label="关闭通知" @click="store.notice = ''">
        <X :size="18" />
      </button>
    </template>
  </div>
</template>
<style scoped>
.session-recovery {
  max-width: 680px;
  margin: 15vh auto;
  padding: 28px;
}
.session-recovery p {
  margin: 18px 0;
  overflow-wrap: anywhere;
}
@media (max-width: 700px) {
  .session-recovery {
    margin: 40px 16px;
    padding: 16px;
  }
}
</style>
