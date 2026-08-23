import { createRouter, createWebHistory } from "vue-router";
import Shell from "../views/Shell.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: "/", name: "shell", component: Shell }],
});
