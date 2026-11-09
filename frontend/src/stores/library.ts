/** 后端业务状态与标签页会话；失效请求不得向界面返回旧身份资料。 */
import { computed, ref } from "vue";
import { defineStore } from "pinia";
import * as api from "../api/client";

export type Role = "reader" | "admin";
export interface Book {
  id: string;
  name: string;
  price: number;
  author: string;
  category: string;
  description: string;
  cover: string;
  createdAt: string;
  publishedAt?: string;
  published: boolean;
  file?: { name: string; format: "TXT"; size: number; url: string };
}
export type BookInput = Omit<Book, "id" | "createdAt" | "publishedAt" | "file">;
export interface Session {
  id: string;
  username: string;
  name: string;
  role: Role;
}

export const useLibraryStore = defineStore("library", () => {
  const books = ref<Book[]>([]);
  const categories = ref<string[]>([]);
  const favoriteBooks = ref<Book[]>([]);
  const favoritesReady = ref(false);
  const favoriteCount = computed(() => favoriteBooks.value.length);
  const session = ref<Session | null>(null);
  const notice = ref("");
  const initialized = ref(false);
  const restoring = ref(false);
  const restoreError = ref("");
  let authGeneration = 0;
  let bookRequest = 0;
  let favoriteRequest = 0;
  let initializeTask: Promise<void> | null = null;
  const isAdmin = computed(() => session.value?.role === "admin");

  /** 判断图书 id 是否属于当前用户的可见收藏。 */
  function isFavorite(id: string): boolean {
    return favoriteBooks.value.some((book) => book.id === id);
  }
  /** 显示全局 message 通知。 */
  function notify(message: string): void {
    notice.value = message;
  }
  /** 使全部旧会话请求失效；不删除令牌或已确认资料，无参数。 */
  function nextGeneration(): number {
    authGeneration++;
    api.invalidateRequests();
    bookRequest++;
    favoriteRequest++;
    initializeTask = null;
    restoring.value = false;
    return authGeneration;
  }
  /** 清空上一个身份的业务副本；无参数。 */
  function clearBusiness(): void {
    books.value = [];
    categories.value = [];
    favoriteBooks.value = [];
    favoritesReady.value = false;
  }
  /** 拒绝 generation 所属的旧会话结果，包含向页面返回的资料。 */
  function assertCurrent(generation: number): void {
    if (generation !== authGeneration) throw new api.RequestCancelled();
  }
  /** 清理 generation 对应的过期会话，迟到错误不得影响新身份。 */
  function expireSession(generation = authGeneration): void {
    if (generation !== authGeneration) return;
    nextGeneration();
    clearBusiness();
    api.clearToken();
    session.value = null;
    initialized.value = true;
    restoreError.value = "";
    notice.value = "登录已过期，请重新登录。";
  }
  /** 运行 operation 并隔离 generation 的成功、401和网络错误。 */
  async function execute<T>(
    generation: number,
    operation: () => Promise<T>,
  ): Promise<T> {
    assertCurrent(generation);
    try {
      const result = await operation();
      assertCurrent(generation);
      return result;
    } catch (error) {
      assertCurrent(generation);
      if (error instanceof api.ApiError && error.status === 401)
        expireSession(generation);
      throw error;
    }
  }
  /** 恢复 generation 对应令牌；网络失败保留令牌并提供显式重试。 */
  async function restore(generation: number): Promise<void> {
    restoring.value = true;
    try {
      if (!sessionStorage.getItem("qingye.access_token")) {
        initialized.value = true;
        return;
      }
      const user = await api.currentUser();
      assertCurrent(generation);
      const favorites = await api.listFavorites();
      assertCurrent(generation);
      session.value = user;
      favoriteBooks.value = favorites;
      favoritesReady.value = true;
      initialized.value = true;
      restoreError.value = "";
    } catch (error) {
      if (generation !== authGeneration || api.isRequestCancelled(error))
        return;
      if (error instanceof api.ApiError && error.status === 401) {
        expireSession(generation);
      } else {
        restoreError.value = `无法验证登录状态：${api.errorMessage(error)}`;
      }
    } finally {
      if (generation === authGeneration) restoring.value = false;
    }
  }
  /** 合并并发身份恢复；无参数，错误状态等待用户重试。 */
  async function initialize(): Promise<void> {
    if (initialized.value || restoreError.value) return;
    if (initializeTask) return initializeTask;
    const task = restore(authGeneration);
    initializeTask = task;
    try {
      await task;
    } finally {
      if (initializeTask === task) initializeTask = null;
    }
  }
  /** 重新验证当前已存令牌；无参数，不伪装成未登录状态。 */
  async function retryInitialize(): Promise<void> {
    if (initializeTask) return initializeTask;
    restoreError.value = "";
    initialized.value = false;
    await initialize();
  }
  /** 用 account、password 与 portal 登录，身份恢复成功后清除旧提示。 */
  async function login(
    account: string,
    password: string,
    portal: "reader" | "admin" = "reader",
  ): Promise<void> {
    const generation = nextGeneration();
    try {
      await api.login(account, password, portal);
      assertCurrent(generation);
      nextGeneration();
      clearBusiness();
      session.value = null;
      initialized.value = false;
      restoreError.value = "";
    } catch (error) {
      assertCurrent(generation);
      throw error;
    }
    await initialize();
    if (session.value && initialized.value && !restoreError.value) {
      notice.value = "";
    }
  }
  /** 用 username、password 注册固定读者账号；不改变当前身份。 */
  async function register(username: string, password: string): Promise<void> {
    const generation = authGeneration;
    await execute(generation, () => api.register(username, password));
  }
  /** 用旧密码与新密码更新当前账户；开始时隔离旧请求，成功后清理会话。 */
  async function changePassword(
    oldPassword: string,
    newPassword: string,
  ): Promise<void> {
    const generation = nextGeneration();
    await execute(generation, () =>
      api.changePassword(oldPassword, newPassword),
    );
    assertCurrent(generation);
    nextGeneration();
    clearBusiness();
    api.clearToken();
    session.value = null;
    initialized.value = true;
    restoreError.value = "";
    notify("密码已修改，请重新登录");
  }
  /** 撤销当前真实会话；成功或401才清理，网络失败保留令牌供重试。 */
  async function logout(): Promise<void> {
    const generation = nextGeneration();
    try {
      await api.logout();
      assertCurrent(generation);
    } catch (error) {
      assertCurrent(generation);
      if (!(error instanceof api.ApiError && error.status === 401)) throw error;
    }
    nextGeneration();
    clearBusiness();
    api.clearToken();
    session.value = null;
    initialized.value = true;
    restoreError.value = "";
  }
  /** 按 params 查询书目分页，同一查询及身份代次才可返回资料。 */
  async function loadBooks(params: {
    q?: string;
    category?: string;
    sort?: string;
    page: number;
    pageSize: number;
    scope?: "all";
  }): Promise<api.PageResult> {
    const requestId = ++bookRequest;
    const result = await execute(authGeneration, () => api.listBooks(params));
    if (requestId !== bookRequest) throw new api.RequestCancelled();
    books.value = result.list;
    return result;
  }
  /** 获取真实已上架分类；无参数。 */
  async function loadCategories(): Promise<void> {
    const generation = authGeneration;
    const result = await execute(generation, api.listCategories);
    assertCurrent(generation);
    categories.value = result;
  }
  /** 返回已上架图书 id，旧会话不向页面返回详情。 */
  async function loadBook(id: string): Promise<Book> {
    return execute(authGeneration, () => api.getBook(id));
  }
  /** 返回当前用户的概览；无参数。 */
  async function loadOverview(): Promise<api.OverviewResult> {
    return execute(authGeneration, api.getOverview);
  }
  /** 获取当前用户收藏，仅最新请求可以更新状态；无参数。 */
  async function loadFavorites(): Promise<void> {
    const requestId = ++favoriteRequest;
    const result = await execute(authGeneration, api.listFavorites);
    if (requestId !== favoriteRequest) throw new api.RequestCancelled();
    favoriteBooks.value = result;
    favoritesReady.value = true;
  }
  /** 切换当前用户对 id 的收藏，写入和刷新沿用同一身份代次。 */
  async function toggleFavorite(id: string): Promise<void> {
    const generation = authGeneration;
    if (!favoritesReady.value) await loadFavorites();
    assertCurrent(generation);
    const target = !isFavorite(id);
    await execute(generation, () => api.setFavorite(id, target));
    assertCurrent(generation);
    await loadFavorites();
    assertCurrent(generation);
    notify(target ? "已加入收藏" : "已取消收藏");
  }
  /** 保存 input，id 省略时新增，返回真实编号；不将刷新失败当成写入失败。 */
  async function saveBook(input: BookInput, id?: string): Promise<string> {
    const generation = authGeneration;
    const saved = await execute(generation, () => api.saveBook(input, id));
    assertCurrent(generation);
    notify("图书资料已保存");
    return String(saved.id);
  }
  /** 删除服务端图书 id，仅当前会话显示成功通知。 */
  async function deleteBook(id: string): Promise<void> {
    const generation = authGeneration;
    await execute(generation, () => api.deleteBook(id));
    assertCurrent(generation);
    notify("图书已删除");
  }
  /** 将图书 id 的上架状态设为 published。 */
  async function setPublished(id: string, published: boolean): Promise<void> {
    const generation = authGeneration;
    await execute(generation, () => api.setPublished(id, published));
    assertCurrent(generation);
    notify(published ? "图书已上架" : "图书已下架");
  }
  /** 鉴权下载图书 id，统一处理失效会话、401和真实网络错误。 */
  async function downloadFile(id: string): Promise<Blob> {
    return execute(authGeneration, () => api.downloadFile(id));
  }

  return {
    books,
    categories,
    favoriteBooks,
    favoritesReady,
    favoriteCount,
    session,
    isAdmin,
    isFavorite,
    notice,
    initialized,
    restoring,
    restoreError,
    initialize,
    retryInitialize,
    register,
    changePassword,
    login,
    logout,
    loadBooks,
    loadCategories,
    loadBook,
    loadOverview,
    loadFavorites,
    toggleFavorite,
    saveBook,
    deleteBook,
    setPublished,
    downloadFile,
    notify,
    expireSession,
  };
});
