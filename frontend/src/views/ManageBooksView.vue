<!-- 管理员图书维护：共享编辑表单、上架操作与具名删除确认。 -->
<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import { Plus, Pencil, Trash2, X } from "lucide-vue-next";
import { errorMessage, isRequestCancelled } from "../api/client";
import { useLibraryStore, type Book, type BookInput } from "../stores/library";
const store = useLibraryStore();
const query = ref("");
const page = ref(1);
const pageSize = 10;
const total = ref(0);
const loading = ref(false);
const listError = ref("");
const pending = ref(false);
const pendingBook = ref("");
const dialog = ref<HTMLDialogElement>();
const mode = ref<"edit" | "delete">("edit");
const editing = ref<string>();
const removing = ref<Book>();
const error = ref("");
let returnFocus: HTMLElement | null = null;
let queryRequest = 0;
const totalPages = computed(() =>
  Math.max(1, Math.ceil(total.value / pageSize)),
);
const form = reactive<BookInput>({
  name: "",
  author: "",
  category: "",
  price: 0,
  description: "",
  cover: "",
  published: true,
});
/** 查询管理员可见的服务端分页，旧响应不得改写当前列表状态。 */
async function loadPage(): Promise<boolean | undefined> {
  const requestId = ++queryRequest;
  loading.value = true;
  listError.value = "";
  try {
    const result = await store.loadBooks({
      q: query.value.trim(),
      page: page.value,
      pageSize,
      scope: "all",
    });
    if (requestId !== queryRequest) return;
    total.value = result.total;
    const lastPage = Math.max(1, Math.ceil(result.total / pageSize));
    if (page.value > lastPage) page.value = lastPage;
    return true;
  } catch (reason) {
    if (isRequestCancelled(reason)) return;
    if (requestId === queryRequest) listError.value = errorMessage(reason);
    return false;
  } finally {
    if (requestId === queryRequest) loading.value = false;
  }
}
/** 搜索词变化时返回第一页并读取服务端匹配结果。 */
watch(query, () => {
  page.value = 1;
});
watch([query, page], loadPage, { immediate: true });
/** 打开新建或编辑表单；book 省略时创建新书。 */
function openEditor(book?: Book) {
  editing.value = book?.id;
  mode.value = "edit";
  error.value = "";
  Object.assign(
    form,
    book
      ? {
          name: book.name,
          author: book.author,
          category: book.category,
          price: book.price,
          description: book.description,
          cover: book.cover,
          published: book.published,
        }
      : {
          name: "",
          author: "",
          category: "",
          price: 0,
          description: "",
          cover: "",
          published: true,
        },
  );
  openDialog();
}
/** 显示删除确认；book 为待删除图书。 */
function confirmDelete(book: Book) {
  removing.value = book;
  mode.value = "delete";
  error.value = "";
  openDialog();
}
/** 展示原生模态框并将焦点放入首个表单项。 */
function openDialog() {
  returnFocus = document.activeElement as HTMLElement;
  dialog.value?.showModal();
  nextTick(() =>
    dialog.value
      ?.querySelector<HTMLElement>(
        mode.value === "edit" ? "input" : "[data-cancel]",
      )
      ?.focus(),
  );
}
/** 关闭模态框并归还原触发焦点，触发项删除时转到新建按钮。 */
function closeDialog() {
  if (pending.value) return;
  dialog.value?.close();
  nextTick(() => {
    if (returnFocus?.isConnected) returnFocus.focus();
    else document.querySelector<HTMLElement>("[data-create]")?.focus();
  });
}
/** 将 Tab 焦点限制在模态窗口内；event 为当前键盘事件。 */
function trapDialogFocus(event: KeyboardEvent) {
  if (event.key !== "Tab") return;
  const items = dialog.value?.querySelectorAll<HTMLElement>(
    "button:not(:disabled), input:not(:disabled), textarea:not(:disabled), select:not(:disabled), a[href]",
  );
  if (!items?.length) {
    event.preventDefault();
    return;
  }
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
/** 保存完整图书资料；成功写入后单独处理列表刷新，避免重复提交。 */
async function save() {
  if (pending.value) return;
  error.value = "";
  if (
    ![form.name, form.author, form.category, form.description].every((value) =>
      value.trim(),
    ) ||
    form.name.trim().length > 100 ||
    form.author.trim().length > 60 ||
    form.category.trim().length > 40 ||
    form.description.trim().length > 3000 ||
    !Number.isFinite(form.price) ||
    form.price < 0
  ) {
    error.value =
      "请完整填写有效资料：书名最多100字、作者60字、分类40字、简介3000字，价格须为非负数。";
    return;
  }
  pending.value = true;
  try {
    await store.saveBook({ ...form }, editing.value);
    closeDialogAfterSuccess();
    if ((await loadPage()) === false)
      store.notify(
        "图书已保存，但列表刷新失败；请使用页面重试，不要重复提交。",
      );
  } catch (reason) {
    if (isRequestCancelled(reason)) return;
    error.value = errorMessage(reason);
  } finally {
    pending.value = false;
  }
}
/** 关闭已成功保存的对话框；不受提交中的普通关闭保护影响。 */
function closeDialogAfterSuccess() {
  dialog.value?.close();
  nextTick(() => {
    if (returnFocus?.isConnected) returnFocus.focus();
    else document.querySelector<HTMLElement>("[data-create]")?.focus();
  });
}
/** 删除已确认图书并刷新管理员列表。 */
async function remove() {
  if (!removing.value || pending.value) return;
  pending.value = true;
  error.value = "";
  try {
    await store.deleteBook(removing.value.id);
    closeDialogAfterSuccess();
    if ((await loadPage()) === false)
      store.notify("图书已删除，但列表刷新失败；请使用页面重试。");
  } catch (reason) {
    if (!isRequestCancelled(reason)) error.value = errorMessage(reason);
  } finally {
    pending.value = false;
  }
}
/** 更新当前图书 book 的上下架状态并刷新管理页。 */
async function togglePublication(book: Book) {
  if (pendingBook.value) return;
  pendingBook.value = book.id;
  try {
    await store.setPublished(book.id, !book.published);
    if ((await loadPage()) === false)
      store.notify("上架状态已更新，但列表刷新失败；请重试列表查询。");
  } catch (reason) {
    if (!isRequestCancelled(reason)) listError.value = errorMessage(reason);
  } finally {
    pendingBook.value = "";
  }
}
/** 将当前页状态移到上一页且不低于第一页；无参数。 */
function previousPage() {
  page.value = Math.max(1, page.value - 1);
}
/** 将当前页状态移到下一页且不超过服务端结果末页；无参数。 */
function nextPage() {
  page.value = Math.min(totalPages.value, page.value + 1);
}
onMounted(() => {
  store.loadCategories().catch((reason) => {
    if (!isRequestCancelled(reason)) listError.value = errorMessage(reason);
  });
});
</script>
<template>
  <main v-if="store.isAdmin" class="management">
    <div class="page-heading">
      <div>
        <h1>图书管理</h1>
      </div>
      <button
        data-create
        class="button"
        :disabled="pending || Boolean(pendingBook)"
        @click="openEditor()"
      >
        <Plus :size="18" />新增图书
      </button>
    </div>
    <div class="manage-toolbar">
      <label class="field"
        >查找图书<input
          v-model="query"
          type="search"
          placeholder="输入书名或作者" /></label
      ><span class="muted">共 {{ total }} 本管理记录</span>
    </div>
    <p v-if="loading" class="muted" role="status">正在读取管理书目…</p>
    <p v-else-if="listError" class="form-error" role="alert">
      {{ listError }}
      <button class="text-button" @click="loadPage">重试</button>
    </p>
    <div class="manage-table">
      <table>
        <thead>
          <tr>
            <th scope="col">图书 / 作者</th>
            <th scope="col">分类</th>
            <th scope="col">价格</th>
            <th scope="col">状态</th>
            <th scope="col">阅读文件</th>
            <th scope="col">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="book in store.books" :key="book.id">
            <td data-label="图书 / 作者">
              <strong>{{ book.name }}</strong
              ><small class="muted">{{ book.author || "未填写作者" }}</small>
            </td>
            <td data-label="分类">{{ book.category || "未填写分类" }}</td>
            <td data-label="价格">¥{{ book.price.toFixed(2) }}</td>
            <td data-label="状态">
              <span class="tag" :class="{ unpublished: !book.published }">{{
                book.published ? "已上架" : "已下架"
              }}</span>
            </td>
            <td data-label="阅读文件">
              <span v-if="book.file">TXT · {{ book.file.size }} 字节</span
              ><span v-else class="muted">暂无文件</span>
            </td>
            <td data-label="操作">
              <div class="row-actions">
                <button
                  class="text-button"
                  :aria-label="'编辑《' + book.name + '》'"
                  :disabled="pending || Boolean(pendingBook)"
                  @click="openEditor(book)"
                >
                  <Pencil :size="15" />编辑</button
                ><button
                  class="text-button"
                  :disabled="Boolean(pendingBook)"
                  :aria-label="
                    (book.published ? '下架' : '上架') + '《' + book.name + '》'
                  "
                  @click="togglePublication(book)"
                >
                  {{
                    pendingBook === book.id
                      ? "处理中…"
                      : book.published
                        ? "下架"
                        : "上架"
                  }}</button
                ><button
                  class="text-button danger-text"
                  :disabled="pending || Boolean(pendingBook)"
                  :aria-label="'删除《' + book.name + '》'"
                  @click="confirmDelete(book)"
                >
                  <Trash2 :size="15" />删除
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div
        v-if="!store.books.length && !loading && !listError"
        class="empty-state"
      >
        <h2>{{ query ? "没有匹配的图书" : "暂无管理书目" }}</h2>
        <p>调整关键词后再找找。</p>
        <button v-if="query" class="button secondary" @click="query = ''">
          清空搜索
        </button>
      </div>
    </div>
    <nav
      v-if="total && !listError"
      class="pagination"
      aria-label="管理列表分页"
    >
      <button
        class="button secondary"
        :disabled="page <= 1 || loading"
        @click="previousPage"
      >
        上一页
      </button>
      <span>第 {{ page }} / {{ totalPages }} 页</span>
      <button
        class="button secondary"
        :disabled="page >= totalPages || loading"
        @click="nextPage"
      >
        下一页
      </button>
    </nav>
    <dialog
      ref="dialog"
      class="manage-dialog"
      aria-labelledby="book-dialog-title"
      @cancel.prevent="closeDialog"
      @keydown="trapDialogFocus"
    >
      <div class="dialog-heading">
        <h2 id="book-dialog-title">
          {{
            mode === "delete"
              ? "确认删除图书"
              : editing
                ? "编辑图书"
                : "新增图书"
          }}
        </h2>
        <button
          class="icon-button"
          aria-label="关闭对话框"
          :disabled="pending"
          @click="closeDialog"
        >
          <X :size="20" />
        </button>
      </div>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <template v-if="mode === 'delete'"
        ><p>确定删除《{{ removing?.name }}》吗？</p>
        <p class="muted">该操作会移除所有用户对此书的收藏，且无法撤销。</p>
        <div class="dialog-actions">
          <button
            data-cancel
            class="button secondary"
            :disabled="pending"
            @click="closeDialog"
          >
            取消</button
          ><button class="button danger" :disabled="pending" @click="remove">
            {{ pending ? "正在删除…" : "确认删除" }}
          </button>
        </div></template
      >
      <form v-else @submit.prevent="save">
        <div class="form-grid">
          <label class="field"
            >书名<input v-model="form.name" required maxlength="100" /></label
          ><label class="field"
            >作者<input v-model="form.author" required maxlength="60" /></label
          ><label class="field"
            >分类<input
              v-model="form.category"
              required
              maxlength="40"
              list="book-categories" /><datalist id="book-categories">
              <option
                v-for="category in store.categories"
                :key="category"
                :value="category"
              /></datalist></label
          ><label class="field"
            >价格（元）<input
              v-model.number="form.price"
              required
              type="number"
              min="0"
              step="0.01"
          /></label>
        </div>
        <label class="field"
          >图书简介<textarea
            v-model="form.description"
            required
            rows="4"
            maxlength="3000"
          ></textarea></label
        ><label class="checkbox-field"
          ><input
            v-model="form.published"
            type="checkbox"
          />保存后上架可见</label
        >
        <p v-if="!editing" class="muted form-help">新书暂不附文件。</p>
        <div class="dialog-actions">
          <button
            type="button"
            class="button secondary"
            :disabled="pending"
            @click="closeDialog"
          >
            取消</button
          ><button class="button" type="submit" :disabled="pending">
            {{ pending ? "正在保存…" : "保存图书" }}
          </button>
        </div>
      </form>
    </dialog>
  </main>
</template>
