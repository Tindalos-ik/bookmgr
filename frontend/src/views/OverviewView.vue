<!-- 读者概览页：提供藏书统计、最近上架书籍与真实书目推荐。 -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { errorMessage, isRequestCancelled } from "../api/client";
import { useLibraryStore } from "../stores/library";
import BookCard from "../components/BookCard.vue";
import BookCover from "../components/BookCover.vue";
import "../assets/catalog.css";

const library = useLibraryStore();
const loading = ref(false);
const error = ref("");
const overview = ref<Awaited<ReturnType<typeof library.loadOverview>>>();
const recommendation = computed(() => overview.value?.recommendation ?? null);
const newestBooks = computed(() => overview.value?.latestBooks ?? []);
const bookCount = computed(() => overview.value?.bookCount ?? 0);
const downloadableCount = computed(
  () => overview.value?.downloadableCount ?? 0,
);
const favoriteCount = computed(() => library.favoriteCount);
/** 查询服务端概览；失败时保留错误并允许用户主动重试。 */
async function loadOverview() {
  loading.value = true;
  error.value = "";
  try {
    overview.value = await library.loadOverview();
  } catch (reason) {
    if (!isRequestCancelled(reason)) error.value = errorMessage(reason);
  } finally {
    loading.value = false;
  }
}
/** 截取简介为推荐区域摘要；description 参数是待显示的书籍简介。 */
function descriptionSummary(description: string): string {
  const text = description.trim();
  return text.length > 150 ? `${text.slice(0, 150)}…` : text || "未填写简介。";
}
onMounted(loadOverview);
</script>

<template>
  <main class="catalog-page overview-page">
    <header class="page-heading">
      <div>
        <h1>概览</h1>
      </div>
    </header>
    <p v-if="loading" class="muted" role="status">正在读取书房概览…</p>
    <section v-else-if="error" class="empty-state" role="alert">
      <h2>概览暂时无法加载</h2>
      <p>{{ error }}</p>
      <button class="button secondary" @click="loadOverview">重试</button>
    </section>
    <template v-else>
      <section class="overview-hero" aria-label="为你推荐">
        <template v-if="recommendation">
          <div class="recommendation-copy">
            <p class="eyebrow">为你推荐</p>
            <h2>{{ recommendation.name }}</h2>
            <p class="recommendation-author">
              {{ recommendation.author || "未填写作者"
              }}<span v-if="recommendation.category">
                · {{ recommendation.category }}</span
              >
            </p>
            <p class="recommendation-description">
              {{ descriptionSummary(recommendation.description) }}
            </p>
            <RouterLink class="button" :to="`/books/${recommendation.id}`"
              >查看书籍详情</RouterLink
            >
          </div>
          <RouterLink
            class="recommendation-cover"
            :to="`/books/${recommendation.id}`"
            :aria-label="`查看《${recommendation.name}》详情`"
            ><BookCover :book="recommendation"
          /></RouterLink>
          <svg
            class="overview-illustration"
            viewBox="0 0 170 150"
            aria-hidden="true"
          >
            <path
              d="M15 126h140"
              fill="none"
              stroke="#28736f"
              stroke-width="3"
              stroke-linecap="round"
            />
            <path
              d="M38 48q23-9 46 2v68q-23-10-46-2z"
              fill="#f2de80"
              stroke="#28736f"
              stroke-width="3"
            />
            <path
              d="M84 50q23-11 47-2v68q-24-9-47 2z"
              fill="#edc1cd"
              stroke="#28736f"
              stroke-width="3"
            />
            <path
              d="M50 70h22m-22 10h22m-22 10h22m24-20h22m-22 10h22m-22 10h22"
              stroke="#28736f"
              stroke-width="2"
              stroke-linecap="round"
            />
          </svg>
        </template>
        <div v-else class="recommendation-empty">
          <h2>书库暂时没有可见书籍</h2>
          <RouterLink class="button secondary" to="/books"
            >前往书籍目录</RouterLink
          >
        </div>
      </section>
      <section class="overview-stats" aria-label="书库统计">
        <article>
          <strong>{{ bookCount }}</strong
          ><span>可见书籍</span>
        </article>
        <article>
          <strong>{{ downloadableCount }}</strong
          ><span>含 TXT 文件</span>
        </article>
        <article>
          <strong>{{ favoriteCount }}</strong
          ><span>我的收藏</span>
        </article>
      </section>
      <section class="overview-section">
        <div class="section-heading">
          <h2>最近上架</h2>
          <RouterLink class="catalog-link" to="/books">浏览全部</RouterLink>
        </div>
        <div v-if="newestBooks.length" class="overview-grid">
          <BookCard v-for="book in newestBooks" :key="book.id" :book="book" />
        </div>
        <div v-else class="empty-state">
          <h2>暂无最近上架的书籍</h2>
          <RouterLink class="button secondary" to="/books">前往目录</RouterLink>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.overview-page {
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
.overview-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(155px, 205px) 150px;
  align-items: center;
  gap: 24px;
  min-height: 220px;
  padding: 24px 30px;
  border: 1px solid #e1eceb;
  border-radius: 16px;
  background: #fff;
}
.recommendation-copy h2 {
  margin: 4px 0 8px;
  font-size: 24px;
  overflow-wrap: anywhere;
}
.eyebrow {
  margin: 0 0 8px;
  color: #28736f;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.recommendation-author,
.recommendation-description {
  color: #65747a;
  line-height: 1.7;
}
.recommendation-description {
  margin: 12px 0;
}
.recommendation-copy .button,
.recommendation-empty .button {
  display: inline-flex;
  margin-top: 6px;
  text-decoration: none;
}
.recommendation-cover {
  display: block;
  width: min(100%, 170px);
  justify-self: center;
  border-radius: 10px;
}
.overview-illustration {
  width: 100%;
}
.recommendation-empty {
  grid-column: 1 / -1;
}
.recommendation-empty h2 {
  margin: 0 0 8px;
  font-size: 20px;
}
.recommendation-empty p:not(.eyebrow) {
  color: #65747a;
}
.overview-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-top: 20px;
}
.overview-stats article {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 17px 20px;
  border: 1px solid #e1eceb;
  border-radius: 12px;
  background: #fff;
}
.overview-stats strong {
  color: #28736f;
  font-size: 26px;
}
.overview-stats span {
  color: #65747a;
  font-size: 13px;
}
.overview-section {
  margin-top: 28px;
}
.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.section-heading h2 {
  margin: 0;
  font-size: 20px;
}
.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}
@media (max-width: 900px) {
  .overview-hero {
    grid-template-columns: minmax(0, 1fr) 170px;
  }
  .overview-illustration {
    display: none;
  }
  .overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 560px) {
  .overview-hero {
    grid-template-columns: minmax(0, 1fr) 100px;
    gap: 14px;
    padding: 20px 16px;
  }
  .recommendation-cover {
    width: 100%;
  }
  .recommendation-copy h2 {
    font-size: 20px;
  }
  .overview-stats {
    gap: 8px;
  }
  .overview-stats article {
    padding: 12px 10px;
  }
  .overview-stats strong {
    font-size: 22px;
  }
  .overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
