<!-- 书籍卡片组件：展示封面与书籍资料，并提供详情和收藏入口。 -->
<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";
import { errorMessage, isRequestCancelled } from "../api/client";
import { useLibraryStore, type Book } from "../stores/library";
import BookCover from "./BookCover.vue";

const props = defineProps<{ book: Book }>();
const library = useLibraryStore();
const favorite = computed(() => library.isFavorite(props.book.id));
const pending = ref(false);
const error = ref("");
/** 更新当前卡片收藏；pending 阻止重复请求，失败时保留原收藏状态。 */
async function toggleFavorite() {
  if (pending.value) return;
  pending.value = true;
  error.value = "";
  try {
    await library.toggleFavorite(props.book.id);
  } catch (reason) {
    if (!isRequestCancelled(reason)) error.value = errorMessage(reason);
  } finally {
    pending.value = false;
  }
}
</script>

<template>
  <article class="book-card">
    <RouterLink
      class="book-card__cover-link"
      :to="`/books/${book.id}`"
      :aria-label="`查看《${book.name}》详情`"
    >
      <BookCover :book="book" />
    </RouterLink>
    <div class="book-card__body">
      <RouterLink class="book-card__title" :to="`/books/${book.id}`">{{
        book.name
      }}</RouterLink>
      <p class="book-card__author">{{ book.author || "未填写作者" }}</p>
      <div class="book-card__tags">
        <span class="tag">{{ book.category || "未填写分类" }}</span>
        <span class="tag">{{ book.file ? "TXT" : "无文件" }}</span>
      </div>
      <div class="book-card__actions">
        <RouterLink class="catalog-link" :to="`/books/${book.id}`"
          >查看详情</RouterLink
        >
        <button
          class="book-card__favorite"
          type="button"
          :disabled="pending || !library.favoritesReady"
          :aria-label="
            favorite ? `取消收藏《${book.name}》` : `收藏《${book.name}》`
          "
          :aria-pressed="favorite"
          @click="toggleFavorite"
        >
          {{ pending ? "保存中…" : favorite ? "已收藏" : "收藏" }}
        </button>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      </div>
    </div>
  </article>
</template>

<style scoped>
.book-card {
  min-width: 0;
  padding: 14px;
  border: 1px solid #e1eceb;
  border-radius: 14px;
  background: #fff;
}
.book-card__cover-link {
  display: block;
  overflow: hidden;
  border-radius: 10px;
}
.book-card__body {
  padding-top: 13px;
}
.book-card__title {
  display: -webkit-box;
  overflow: hidden;
  min-height: 3em;
  color: #242936;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.5;
  text-decoration: none;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.book-card__title:hover {
  color: #28736f;
}
.book-card__author {
  overflow: hidden;
  margin: 7px 0 12px;
  color: #65747a;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.book-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.book-card__actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
}
.book-card__favorite {
  padding: 5px 8px;
  border: 1px solid #e1eceb;
  border-radius: 8px;
  color: #28736f;
  background: white;
  cursor: pointer;
  font-size: 13px;
}
.book-card__favorite:hover {
  background: #e7f7f9;
}
@media (prefers-reduced-motion: no-preference) {
  .book-card {
    transition: transform 150ms ease;
  }
  .book-card:hover {
    transform: translateY(-2px);
  }
}
</style>
