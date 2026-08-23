import { createRouter, createWebHistory } from "vue-router";
import Shell from "../views/Shell.vue";
import MapScreen from "../views/MapScreen.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "shell", component: Shell },
    { path: "/map", name: "map", component: MapScreen },
  ],
});
