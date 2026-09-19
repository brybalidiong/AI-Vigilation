import { createRouter, createWebHistory } from "vue-router";
import { onAuthStateChanged } from "firebase/auth";
import { auth } from "@/firebase";

const LoginView = () => import("@/views/LoginView.vue");
const StudentDashboardView = () => import("@/views/StudentDashboardView.vue");
const AdminLoginView = () => import("@/views/AdminLoginView.vue");
const AdminDashboardView = () => import("@/views/AdminDashboardView.vue");
const InstructorDashboardView = () => import("@/views/InstructorDashboardView.vue");

const routes = [
  { path: "/", component: LoginView },
  { path: "/admin/login", component: AdminLoginView },
  {
    path: "/admin/dashboard",
    component: AdminDashboardView,
    meta: { requiresAuth: true, role: "admin" },
  },
  { path: "/dashboard", redirect: "/student/dashboard" },
  {
    path: "/student/dashboard",
    component: StudentDashboardView,
    meta: { requiresAuth: true, role: "student" },
  },
  {
    path: "/student/courses",
    component: StudentDashboardView,
    meta: { requiresAuth: true, role: "student" },
  },
  {
    path: "/student/settings",
    component: StudentDashboardView,
    meta: { requiresAuth: true, role: "student" },
  },
  {
    path: "/student/courses/:courseId",
    component: StudentDashboardView,
    meta: { requiresAuth: true, role: "student" },
  },
  {
    path: "/instructor/dashboard",
    component: InstructorDashboardView,
    meta: { requiresAuth: true, role: "instructor" },
  },
  {
    path: "/instructor/courses",
    component: InstructorDashboardView,
    meta: { requiresAuth: true, role: "instructor" },
  },
  {
    path: "/instructor/settings",
    component: InstructorDashboardView,
    meta: { requiresAuth: true, role: "instructor" },
  },
  {
    path: "/instructor/courses/:courseId",
    component: InstructorDashboardView,
    meta: { requiresAuth: true, role: "instructor" },
  },
  {
    path: "/instructor/courses/:courseId/sets/:setId",
    component: InstructorDashboardView,
    meta: { requiresAuth: true, role: "instructor" },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

let authResolved = false;
const authReady = new Promise((resolve) => {
  onAuthStateChanged(auth, () => {
    authResolved = true;
    resolve(true);
  });
});

function getStoredRole() {
  try {
    const raw = localStorage.getItem("user");
    if (raw) {
      const u = JSON.parse(raw);
      if (u?.role) return u.role;
    }
  } catch {
    /* ignore */
  }
  return localStorage.getItem("role") || "";
}

router.beforeEach(async (to) => {
  if (!authResolved) {
    await authReady;
  }

  const role = getStoredRole();

  if (to.meta.role === "admin") {
    const token = localStorage.getItem("access_token");
    if (!token || role !== "admin") {
      return "/admin/login";
    }
  }

  if (to.meta.role === "student") {
    if (!auth.currentUser) {
      return "/";
    }
    if (role && role !== "student") {
      if (role === "instructor") return "/instructor/dashboard";
      if (role === "admin") return "/admin/dashboard";
      return "/";
    }
  }

  if (to.meta.role === "instructor") {
    const token = localStorage.getItem("access_token");
    if (!token || role !== "instructor") {
      return "/";
    }
  }
});

export default router;
