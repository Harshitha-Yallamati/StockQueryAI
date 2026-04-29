import React, { createContext, useContext, useState, useEffect } from 'react';
import { auth } from '@/lib/firebase';
import { 
  User as FirebaseUser,
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword, 
  signInWithPopup, 
  GoogleAuthProvider, 
  signOut, 
  onAuthStateChanged,
  updateProfile
} from 'firebase/auth';

interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name: string) => Promise<void>;
  googleLogin: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);
const DEMO_AUTH_TIMEOUT_MS = 2000;

function mapFirebaseUser(firebaseUser: FirebaseUser): User {
  return {
    id: firebaseUser.uid,
    email: firebaseUser.email || '',
    name: firebaseUser.displayName || firebaseUser.email?.split('@')[0] || 'User',
    picture: firebaseUser.photoURL || undefined,
  };
}

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let resolved = false;
    const fallbackTimer = window.setTimeout(() => {
      if (resolved) return;
      setUser(null);
      setLoading(false);
    }, DEMO_AUTH_TIMEOUT_MS);

    const unsubscribe = onAuthStateChanged(
      auth,
      (firebaseUser) => {
        resolved = true;
        window.clearTimeout(fallbackTimer);
        if (firebaseUser) {
          setUser(mapFirebaseUser(firebaseUser));
        } else {
          setUser(null);
        }
        setLoading(false);
      },
      () => {
        resolved = true;
        window.clearTimeout(fallbackTimer);
        setUser(null);
        setLoading(false);
      },
    );

    return () => {
      resolved = true;
      window.clearTimeout(fallbackTimer);
      unsubscribe();
    };
  }, []);

  const login = async (email: string, password: string) => {
    await signInWithEmailAndPassword(auth, email, password);
  };

  const signup = async (email: string, password: string, name: string) => {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    if (userCredential.user) {
      await updateProfile(userCredential.user, { displayName: name });
      setUser({
        id: userCredential.user.uid,
        email: userCredential.user.email || email,
        name: name,
        picture: userCredential.user.photoURL || undefined
      });
    }
  };

  const googleLogin = async () => {
    const provider = new GoogleAuthProvider();
    await signInWithPopup(auth, provider);
  };

  const logout = async () => {
    try {
      await signOut(auth);
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, googleLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
