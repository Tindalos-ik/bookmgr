<!-- 书籍目录页：支持后端搜索、分类筛选、排序与服务端分页。 -->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { errorMessage, isRequestCancelled } from "../api/client";
import { useLibraryStore } from "../stores/library";
import BookCard from "../components/BookCard.vue";
import "../assets/catalog.css";

const library = useLibraryStore();
const search = ref("");
const category = ref("");
const sorting = ref<"newest" | "name" | "author">("newest");
const page = ref(1);
const pageSize = 8;
const total = ref(0);
const loading = ref(false);
const error = ref("");
const totalPages = computed(() =>
  Math.max(1, Math.ceil(total.value / pageSize)),
);
let queryRequest = 0;
/** 查询当前服务端分页；仅最新查询可更新总量、错误与加载状态。 */
async function loadPage() {
  const requestId = ++queryRequest;
  loading.value = true;
  error.value = "";
  try {
    const result = await library.loadBooks({
      q: search.value.trim(),
      category: category.value,
      sort: sorting.value,
      page: page.value,
      pageSize,
    });
    if (requestId !== queryRequest) return;
    total.value = result.total;
    const lastPage = Math.max(1, Math.ceil(result.total / pageSize));
    if (page.value > lastPage) page.value = lastPage;
  } catch (reason) {
    if (isRequestCancelled(reason)) return;
    if (requestId === queryRequest) error.value = errorMessage(reason);
  } finally {
    if (requestId === queryRequest) loading.value = false;
  }
}
/** 搜索条件变化时回到第一页，避免显示空的旧页码。 */
watch([search, category, sorting], () => {
  page.value = 1;
});
watch([search, category, sorting, page], loadPage, { immediate: true });
/** 清空目录搜索和分类条件。 */
function clearFilters() {
  search.value = "";
  category.value = "";
  page.value = 1;
}
/** 将目录翻到前一页，且不越过第一页。 */
function previousPage() {
  page.value = Math.max(1, page.value - 1);
}
/** 将目录翻到后一页，且不越过末页。 */
function nextPage() {
  page.value = Math.min(totalPages.value, page.value + 1);
}
onMounted(() => {
  library.loadCategories().catch((reason) => {
    if (!isRequestCancelled(reason)) error.value = errorMessage(reason);
  });
});
</script>

<template>
  <main class="catalog-page books-page">
    <header class="page-heading">
      <div>
        <h1>书籍目录</h1>
      </div>
    </header>
    <section class="catalog-controls" aria-label="目录筛选">
      <label class="control-field"
        ><span>搜索书名或作者</span
        ><input
          v-model="search"
          class="field"
          type="search"
          placeholder="输入书名或作者"
      /></label>
      <label class="control-field"
        ><span>书籍分类</span
        ><select v-model="category" class="field">
          <option value="">全部分类</option>
          <option v-for="item in library.categories" :key="item" :value="item">
            {{ item }}
          </option>
        </select></label
      >
      <label class="control-field"
        ><span>排序方式</span
        ><select v-model="sorting" class="field">
          <option value="newest">最近上架</option>
          <option value="name">书名</option>
          <option value="author">作者</option>
        </select></label
      >
    </section>
    <div class="results-line">
      <span>共 {{ total }} 本</span
      ><span v-if="total">第 {{ page }} / {{ totalPages }} 页</span>
    </div>
    <p v-if="loading" class="muted" role="status">正在加载书目…</p>
    <section v-else-if="error" class="empty-state catalog-empty" role="alert">
      <h2>目录加载失败</h2>
      <p>{{ error }}</p>
      <button class="button secondary" @click="loadPage">重试</button>
    </section>
    <section
      v-else-if="library.books.length"
      class="books-grid"
      aria-label="书籍结果"
    >
      <BookCard v-for="book in library.books" :key="book.id" :book="book" />
    </section>
    <section v-else class="empty-state catalog-empty">
      <h2>
        {{ search || category ? "没有找到匹配的书籍" : "书库暂时没有可见书籍" }}
      </h2>
      <p>
        {{
          search || category
            ? "试试调整搜索词或分类筛选。"
            : "新书加入后会显示在这里。"
        }}
      </p>
      <button
        v-if="search || category"
        class="button secondary"
        type="button"
        @click="clearFilters"
      >
        清除筛选
      </button>
    </section>
    <nav v-if="total && !error" class="pagination" aria-label="目录分页">
      <button
        class="button secondary"
        type="button"
        :disabled="page <= 1 || loading"
        @click="previousPage"
      >
        上一页
      </button>
      <span>第 {{ page }} / {{ totalPages }} 页</span>
      <button
        class="button secondary"
        type="button"
        :disabled="page >= totalPages || loading"
        @click="nextPage"
      >
        下一页
      </button>
    </nav>
  </main>
</template>

<style scoped>
.books-page {
  max-width: 1180px;
  margin: 0 auto;
}
.page-heading {
  margin-bottom: 22px;
}
.page-heading h1 {
  margin: 0;
  font-size: 30px;
}
.page-heading .muted {
  margin: 8px 0 0;
}
.catalog-controls {
  display: grid;
  grid-template-columns: minmax(220px, 2fr) repeat(2, minmax(160px, 1fr));
  gap: 14px;
  padding: 18px;
  border: 1px solid #e1eceb;
  border-radius: 14px;
  background: #fff;
}
.control-field {
  display: grid;
  gap: 7px;
  color: #242936;
  font-size: 14px;
  font-weight: 600;
}
.control-field .field {
  width: 100%;
  min-height: 42px;
  padding: 8px 11px;
  border: 1px solid #e1eceb;
  border-radius: 9px;
  color: #242936;
  background: #fff;
}
.results-line {
  display: flex;
  justify-content: space-between;
  margin: 18px 2px 12px;
  color: #65747a;
  font-size: 14px;
}
.books-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}
.catalog-empty {
  margin-top: 18px;
  padding: 34px 20px;
}
.catalog-empty h2 {
  margin-top: 0;
  color: #242936;
  font-size: 19px;
}
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
  color: #65747a;
}
.pagination button:disabled {
  opacity: 0.52;
  cursor: not-allowed;
}
@media (max-width: 960px) {
  .books-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 720px) {
  .books-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .catalog-controls {
    grid-template-columns: 1fr 1fr;
  }
  .control-field:first-child {
    grid-column: 1 / -1;
  }
}
@media (max-width: 480px) {
  .books-grid {
    grid-template-columns: 1fr;
  }
  .catalog-controls {
    grid-template-columns: 1fr;
    padding: 14px;
  }
  .control-field:first-child {
    grid-column: auto;
  }
}
</style>
