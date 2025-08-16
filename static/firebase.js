// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyCgF366Ft7RkZHYaZb77HboNO3BPbmCjT8",
  authDomain: "portal-de-proposta.firebaseapp.com",
  projectId: "portal-de-proposta",
  storageBucket: "portal-de-proposta.firebasestorage.app",
  messagingSenderId: "321036073908",
  appId: "1:321036073908:web:3149b9ea2cb77a704890e1",
  measurementId: "G-CFFVQGM3EC"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
