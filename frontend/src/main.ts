/** 安装应用路由、共享状态及公共样式。 */
import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./assets/main.css";
const app = createApp(App);
/** 停止应用并显示未预期故障；error 为原始异常。 */
function stopApplication(error: unknown) {
  app.unmount();
  const section = document.createElement("section");
  section.className = "fatal-error";
  section.setAttribute("role", "alert");
  const heading = document.createElement("h1");
  heading.textContent = "书房已停止运行";
  const message = document.createElement("p");
  message.textContent = `出现未预期错误：${error instanceof Error ? error.message : String(error)}。\n请检查浏览器存储及控制台信息，解决后刷新页面。`;
  section.append(heading, message);
  document.getElementById("app")!.replaceChildren(section);
  throw error;
}
app.config.errorHandler = stopApplication;
try {
  app.use(createPinia()).use(router).mount("#app");
} catch (error) {
  stopApplication(error);
}
