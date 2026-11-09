<!-- 书籍详情页：展示后端可见书目、收藏状态及鉴权文件下载操作。 -->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { errorMessage, isRequestCancelled } from "../api/client";
import { useLibraryStore, type Book } from "../stores/library";
import BookCover from "../components/BookCover.vue";
import "../assets/catalog.css";

const route = useRoute();
const library = useLibraryStore();
const book = ref<Book | null>(null);
const loading = ref(true);
const error = ref("");
const downloading = ref(false);
const downloadError = ref("");
const favoriteError = ref("");
const favoritePending = ref(false);
const favorite = computed(() =>
  book.value ? library.isFavorite(book.value.id) : false,
);
let detailRequest = 0;
/** 按路由编号读取详情；requestId 防止旧详情覆盖新路由。 */
async function loadBook() {
  const requestId = ++detailRequest;
  loading.value = true;
  error.value = "";
  book.value = null;
  try {
    const result = await library.loadBook(String(route.params.id));
    if (requestId === detailRequest) book.value = result;
  } catch (reason) {
    if (isRequestCancelled(reason)) return;
    if (requestId === detailRequest) error.value = errorMessage(reason);
  } finally {
    if (requestId === detailRequest) loading.value = false;
  }
}
/** 切换当前书籍收藏并仅在后端确认后更新提示。 */
async function toggleFavorite() {
  if (!book.value || favoritePending.value) return;
  favoritePending.value = true;
  favoriteError.value = "";
  try {
    await library.toggleFavorite(book.value.id);
  } catch (reason) {
    if (!isRequestCancelled(reason)) favoriteError.value = errorMessage(reason);
  } finally {
    favoritePending.value = false;
  }
}
/** 携带会话令牌下载捕获的图书文件；bookId 与 file 来自本次点击时书籍。 */
async function downloadBook() {
  const selectedBook = book.value;
  const file = selectedBook?.file;
  if (!selectedBook || !file || downloading.value) return;
  downloading.value = true;
  downloadError.value = "";
  try {
    const blob = await library.downloadFile(selectedBook.id);
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = file.name;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    library.notify("已开始下载");
  } catch (reason) {
    if (isRequestCancelled(reason)) return;
    downloadError.value = `下载失败：${errorMessage(reason)}`;
  } finally {
    downloading.value = false;
  }
}
/** 格式化文件字节数；size 为后端提供的文件大小。 */
function formatBytes(size: number): string {
  if (size < 1024) return `${size} 字节`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}
watch(
  () => route.params.id,
  () => {
    downloadError.value = "";
    favoriteError.value = "";
    void loadBook();
  },
  { immediate: true },
);
</script>

<template>
  <main class="catalog-page detail-page">
    <RouterLink class="catalog-link back-link" to="/books"
      >返回书籍目录</RouterLink
    >
    <p v-if="loading" class="muted" role="status">正在加载书籍资料…</p>
    <section
      v-else-if="error"
      class="empty-state unavailable-state"
      role="alert"
    >
      <h1>暂时无法查看这本书</h1>
      <p>{{ error }}</p>
      <button class="button secondary" @click="loadBook">重试</button>
      <RouterLink class="button secondary" to="/books">返回书籍目录</RouterLink>
    </section>
    <section v-else-if="book" class="detail-layout">
      <div class="detail-cover"><BookCover :book="book" /></div>
      <div class="detail-content">
        <h1>{{ book.name }}</h1>
        <dl class="book-facts">
          <div>
            <dt>作者</dt>
            <dd>{{ book.author || "未填写" }}</dd>
          </div>
          <div>
            <dt>分类</dt>
            <dd>{{ book.category || "未填写" }}</dd>
          </div>
          <div>
            <dt>资料价格</dt>
            <dd>¥{{ Number(book.price).toFixed(2) }}</dd>
          </div>
          <div>
            <dt>加入日期</dt>
            <dd>
              {{
                new Date(book.createdAt).toLocaleDateString("zh-CN", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })
              }}
            </dd>
          </div>
        </dl>
        <section class="description">
          <h2>内容简介</h2>
          <p>{{ book.description || "暂无简介。" }}</p>
        </section>
        <section class="file-info">
          <h2>文件</h2>
          <template v-if="book.file"
            ><p>
              {{ book.file.name }} · {{ book.file.format }} ·
              {{ formatBytes(book.file.size) }}
            </p>
            <button
              class="button"
              type="button"
              :disabled="downloading"
              @click="downloadBook"
            >
              {{ downloading ? "正在下载…" : "下载 TXT 文件" }}
            </button>
            <p v-if="downloadError" class="download-error" role="alert">
              {{ downloadError }}
            </p></template
          >
          <p v-else class="muted">此书暂无可下载文件。</p>
        </section>
        <button
          class="button secondary favorite-button"
          type="button"
          :disabled="favoritePending"
          :aria-pressed="favorite"
          @click="toggleFavorite"
        >
          {{
            favoritePending ? "正在保存…" : favorite ? "取消收藏" : "加入收藏"
          }}
        </button>
        <p v-if="favoriteError" class="download-error" role="alert">
          {{ favoriteError }}
        </p>
      </div>
    </section>
  </main>
</template>

<style scoped>
.detail-page {
  max-width: 1080px;
  margin: 0 auto;
}
.back-link {
  display: inline-block;
  margin-bottom: 20px;
}
.detail-layout {
  display: grid;
  grid-template-columns: minmax(210px, 300px) minmax(0, 1fr);
  align-items: start;
  gap: 34px;
  padding: 26px;
  border: 1px solid #e1eceb;
  border-radius: 16px;
  background: #fff;
}
.detail-cover {
  width: 100%;
  max-width: 300px;
}
.detail-content {
  min-width: 0;
}
.detail-content h1 {
  margin: 0 0 22px;
  font-size: 30px;
  line-height: 1.3;
  overflow-wrap: anywhere;
}
.eyebrow {
  margin: 0 0 8px;
  color: #28736f;
  font-size: 13px;
  font-weight: 700;
}
.book-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 22px;
  margin: 0;
}
.book-facts div {
  min-width: 0;
}
.book-facts dt {
  margin-bottom: 4px;
  color: #65747a;
  font-size: 13px;
}
.book-facts dd {
  margin: 0;
  color: #242936;
  overflow-wrap: anywhere;
}
.description,
.file-info {
  margin-top: 24px;
}
.description h2,
.file-info h2 {
  margin: 0 0 8px;
  font-size: 18px;
}
.description p,
.file-info p {
  color: #65747a;
  line-height: 1.75;
  overflow-wrap: anywhere;
}
.file-info .button {
  margin-top: 4px;
}
.download-error {
  color: #a23d48 !important;
}
.favorite-button {
  margin-top: 20px;
}
.unavailable-state {
  margin: 40px auto;
  max-width: 620px;
  padding: 36px 20px;
}
.unavailable-state h1 {
  margin-top: 0;
  font-size: 23px;
}
.unavailable-state .button {
  display: inline-flex;
  margin-top: 8px;
  text-decoration: none;
}
@media (max-width: 620px) {
  .detail-layout {
    grid-template-columns: 1fr;
    gap: 22px;
    padding: 18px;
  }
  .detail-cover {
    width: min(68%, 260px);
    margin: 0 auto;
  }
  .detail-content h1 {
    font-size: 25px;
  }
}
@media (max-width: 380px) {
  .book-facts {
    grid-template-columns: 1fr;
    gap: 10px;
  }
}
</style>
