<!-- 书房导航布局，移动抽屉支持键盘循环与焦点归还。 -->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  BookOpen,
  LayoutDashboard,
  Library,
  Heart,
  Settings2,
  LogOut,
  Menu,
  X,
} from "lucide-vue-next";
import { ApiError, errorMessage, isRequestCancelled } from "../api/client";
import { useLibraryStore } from "../stores/library";
const store = useLibraryStore(),
  route = useRoute(),
  router = useRouter();
const drawer = ref(false),
  panel = ref<HTMLElement>(),
  trigger = ref<HTMLButtonElement>();
const logoutPending = ref(false);
const links = computed(() => [
  { to: "/overview", label: "书房概览", icon: LayoutDashboard },
  { to: "/books", label: "全部图书", icon: Library },
  { to: "/favorites", label: "我的收藏", icon: Heart },
  ...(store.isAdmin
    ? [{ to: "/manage/books", label: "图书管理", icon: Settings2 }]
    : []),
]);
watch(
  () => route.fullPath,
  () => closeDrawer(),
);
watch(drawer, async (open) => {
  document.body.style.overflow = open ? "hidden" : "";
  if (open) {
    await nextTick();
    panel.value?.querySelector<HTMLElement>("button, a")?.focus();
  }
});
/** 关闭抽屉并将焦点归还导航触发按钮。 */
function closeDrawer() {
  if (drawer.value) {
    drawer.value = false;
    nextTick(() => trigger.value?.focus());
  }
}
/** 在打开的抽屉内处理 Escape 与 Tab；event 为键盘事件。 */
function onKey(event: KeyboardEvent) {
  if (!drawer.value) return;
  if (event.key === "Escape") {
    event.preventDefault();
    closeDrawer();
  }
  if (event.key === "Tab") {
    const items = panel.value?.querySelectorAll<HTMLElement>("a, button");
    if (!items?.length) return;
    const first = items[0]!,
      last = items[items.length - 1]!;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
}
/** 请求服务端注销；网络失败时保留会话并显示可重试错误。 */
async function logout() {
  if (logoutPending.value) return;
  logoutPending.value = true;
  try {
    await store.logout();
    await router.push("/login");
  } catch (reason) {
    if (isRequestCancelled(reason)) return;
    if (reason instanceof ApiError && reason.status === 401) {
      await router.push("/login");
    } else {
      store.notify(`退出失败，服务端尚未确认注销：${errorMessage(reason)}`);
    }
  } finally {
    logoutPending.value = false;
  }
}
</script>
<template>
  <div class="workspace" @keydown="onKey">
    <div v-if="drawer" class="drawer-backdrop" @click="closeDrawer"></div>
    <aside
      ref="panel"
      class="sidebar"
      :class="{ open: drawer }"
      :role="drawer ? 'dialog' : undefined"
      :aria-modal="drawer ? true : undefined"
      aria-label="书房导航"
    >
      <div class="brand">
        <BookOpen :size="27" /><span>青叶书房</span
        ><button
          class="drawer-close icon-button"
          aria-label="关闭导航"
          @click="closeDrawer"
        >
          <X :size="20" />
        </button>
      </div>
      <nav>
        <RouterLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          :class="{
            selected:
              route.path === link.to ||
              (link.to === '/books' && route.path.startsWith('/books/')),
          }"
          ><component :is="link.icon" :size="20" />{{ link.label }}</RouterLink
        >
      </nav>
    </aside>
    <div class="workspace-main">
      <header class="topbar">
        <div>
          <button
            ref="trigger"
            class="mobile-menu icon-button"
            aria-label="打开导航"
            :aria-expanded="drawer"
            @click="drawer = true"
          >
            <Menu :size="22" /></button
          ><span>{{ route.meta.title }}</span>
        </div>
        <div class="account">
          <span class="avatar">{{ store.session?.name.slice(0, 1) }}</span
          ><span>{{ store.session?.name }}</span
          ><button
            class="icon-button"
            title="退出登录"
            aria-label="退出登录"
            :disabled="logoutPending"
            :aria-busy="logoutPending"
            @click="logout"
          >
            <LogOut :size="19" />
          </button>
        </div>
      </header>
      <div class="page-content" id="main-content"><RouterView /></div>
    </div>
  </div>
</template>
