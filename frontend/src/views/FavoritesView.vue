<!-- 收藏页：只呈现当前账号收藏的书籍，可直接取消收藏或打开详情。 -->
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { errorMessage, isRequestCancelled } from "../api/client";
import { useLibraryStore } from "../stores/library";
import BookCard from "../components/BookCard.vue";
import "../assets/catalog.css";
const library = useLibraryStore();
const loading = ref(false);
const error = ref("");
/** 读取当前账号的后端收藏，失败时保留明确错误及重试操作。 */
async function loadFavorites() {
  loading.value = true;
  error.value = "";
  try {
    await library.loadFavorites();
  } catch (reason) {
    if (!isRequestCancelled(reason)) error.value = errorMessage(reason);
  } finally {
    loading.value = false;
  }
}
onMounted(loadFavorites);
</script>

<template>
  <main class="catalog-page favorites-page">
    <header class="page-heading">
      <div>
        <h1>我的收藏</h1>
        <p class="muted favorite-count">
          已收藏 {{ library.favoriteBooks.length }} 本
        </p>
      </div>
    </header>
    <p v-if="loading" class="muted" role="status">正在读取收藏…</p>
    <section v-else-if="error" class="empty-state favorite-empty" role="alert">
      <h2>收藏暂时无法加载</h2>
      <p>{{ error }}</p>
      <button class="button secondary" @click="loadFavorites">重试</button>
    </section>
    <section
      v-else-if="library.favoriteBooks.length"
      class="favorites-grid"
      aria-label="收藏书籍"
    >
      <BookCard
        v-for="book in library.favoriteBooks"
        :key="book.id"
        :book="book"
      />
    </section>
    <section v-else class="empty-state favorite-empty">
      <h2>这里还没有收藏</h2>
      <p>在书籍目录中收藏感兴趣的书，稍后可以从这里继续查看。</p>
      <RouterLink class="button secondary" to="/books">前往书籍目录</RouterLink>
    </section>
  </main>
</template>

<style scoped>
.favorites-page {
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
.favorites-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}
.favorite-empty {
  padding: 36px 20px;
}
.favorite-empty h2 {
  margin-top: 0;
  color: #242936;
  font-size: 20px;
}
.favorite-empty .button {
  display: inline-flex;
  margin-top: 8px;
  text-decoration: none;
}
@media (max-width: 960px) {
  .favorites-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 720px) {
  .favorites-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 480px) {
  .favorites-grid {
    grid-template-columns: 1fr;
  }
}
</style>
