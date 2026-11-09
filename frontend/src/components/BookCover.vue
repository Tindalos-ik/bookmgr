<!-- 书籍封面组件：显示书籍图片，加载失败时以书名生成纯 CSS 封面。 -->
<script setup lang="ts">
import { ref, watch } from "vue";
import type { Book } from "../stores/library";

const props = defineProps<{ book: Book }>();
const imageFailed = ref(false);

/** 图片地址变化时重新尝试加载，避免沿用上一本书的失败状态。 */
watch(
  () => props.book.cover,
  () => {
    imageFailed.value = false;
  },
);
</script>

<template>
  <div
    class="book-cover"
    :class="{ 'book-cover--fallback': imageFailed || !book.cover }"
  >
    <img
      v-if="book.cover && !imageFailed"
      :src="book.cover"
      :alt="`${book.name}封面`"
      @error="imageFailed = true"
    />
    <div
      v-else
      class="book-cover__fallback"
      role="img"
      :aria-label="`${book.name}封面`"
    >
      <span class="book-cover__mark" aria-hidden="true">阅</span>
      <span class="book-cover__title" aria-hidden="true">{{ book.name }}</span>
      <span class="book-cover__rule" aria-hidden="true"></span>
    </div>
  </div>
</template>

<style scoped>
.book-cover {
  position: relative;
  overflow: hidden;
  width: 100%;
  aspect-ratio: 2 / 3;
  border-radius: 10px;
  background: #e7f7f9;
}
.book-cover img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.book-cover__fallback {
  display: flex;
  height: 100%;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 10%;
  padding: 12%;
  color: #28736f;
  background: linear-gradient(145deg, #f7fcfc, #dcefee);
  text-align: center;
}
.book-cover__mark {
  display: grid;
  width: 30%;
  aspect-ratio: 1;
  place-items: center;
  border: 1px solid #91c4bf;
  border-radius: 50%;
  font-size: clamp(12px, 2vw, 20px);
}
.book-cover__title {
  display: -webkit-box;
  overflow: hidden;
  max-width: 100%;
  color: #242936;
  font-size: clamp(12px, 1.4vw, 18px);
  font-weight: 700;
  line-height: 1.5;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}
.book-cover__rule {
  width: 40%;
  height: 2px;
  background: #f2de80;
}
</style>
