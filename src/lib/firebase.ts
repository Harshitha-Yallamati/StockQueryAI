import { initializeApp } from "firebase/app";
import { getAnalytics, isSupported } from "firebase/analytics";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyBnV4hgj11hkrNwZjcM2EzoMaazipAbU9Y",
  authDomain: "stockqueryai.firebaseapp.com",
  projectId: "stockqueryai",
  storageBucket: "stockqueryai.firebasestorage.app",
  messagingSenderId: "957645595663",
  appId: "1:957645595663:web:e27e69212d50e223f0ef7a",
  measurementId: "G-0TBTTQR25Q"
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

isSupported().then((yes) => yes ? getAnalytics(app) : null).catch(() => {});