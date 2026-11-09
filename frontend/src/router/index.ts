/* 路由表与经后端身份验证的权限守卫。 */
import { createRouter, createWebHistory } from "vue-router";
import { useLibraryStore } from "../stores/library";
import Layout from "../components/Layout.vue";
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      component: () => import("../views/LoginView.vue"),
      meta: { guestOnly: true, portal: "reader", title: "用户登录" },
    },
    {
      path: "/admin/login",
      component: () => import("../views/LoginView.vue"),
      meta: { guestOnly: true, portal: "admin", title: "管理员登录" },
    },
    {
      path: "/register",
      component: () => import("../views/RegisterView.vue"),
      meta: { guestOnly: true, title: "注册账号" },
    },
    {
      path: "/",
      component: Layout,
      children: [
        {
          path: "",
          component: () => import("../views/OverviewView.vue"),
          meta: { title: "书房概览" },
        },
        {
          path: "overview",
          component: () => import("../views/OverviewView.vue"),
          meta: { title: "书房概览" },
        },
        {
          path: "books",
          component: () => import("../views/BooksView.vue"),
          meta: { title: "全部图书" },
        },
        {
          path: "books/:id",
          component: () => import("../views/BookDetailView.vue"),
          meta: { title: "图书详情" },
        },
        {
          path: "favorites",
          component: () => import("../views/FavoritesView.vue"),
          meta: { title: "我的收藏" },
        },
        {
          path: "manage/books",
          component: () => import("../views/ManageBooksView.vue"),
          meta: { title: "图书管理", admin: true },
        },
        {
          path: "change-password",
          component: () => import("../views/ChangePasswordView.vue"),
          meta: { title: "修改密码" },
        },
        {
          path: ":pathMatch(.*)*",
          component: () => import("../views/NotFoundView.vue"),
          meta: { title: "页面未找到" },
        },
      ],
    },
  ],
});
router.beforeEach(async (to) => {
  const store = useLibraryStore();
  await store.initialize();
  if (store.restoreError) return true;
  if (!store.initialized) return false;
  if (!store.session && !to.meta.guestOnly) return "/login";
  if (store.session && to.path === "/") {
    return store.isAdmin ? "/manage/books" : "/overview";
  }
  if (store.session && to.meta.guestOnly) {
    return store.isAdmin ? "/manage/books" : "/overview";
  }
  if (to.meta.admin && !store.isAdmin) {
    store.notify("当前读者身份没有图书管理权限");
    return "/overview";
  }
  document.title = String(to.meta.title || "登录") + " · 青叶书房";
});
export default router;
