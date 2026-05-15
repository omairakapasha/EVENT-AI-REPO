import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1";

// Roles allowed to access the admin portal
const ALLOWED_ROLES = ["admin", "owner"];

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        try {
          const res = await fetch(`${API_URL}/users/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials?.email,
              password: credentials?.password,
            }),
          });

          if (!res.ok) return null;

          const data = await res.json();

          // RBAC: Only allow admin/owner roles into the admin portal
          const userRole = data.data?.user?.role?.toLowerCase();
          if (!userRole || !ALLOWED_ROLES.includes(userRole)) {
            // Reject login for non-admin users
            return null;
          }

          return {
            id: data.data?.user?.id || "1",
            name: `${data.data?.user?.first_name || ""} ${data.data?.user?.last_name || ""}`.trim() || "Admin",
            email: data.data?.user?.email || (credentials?.email as string),
            accessToken: data.data?.token,
            role: userRole,
          };
        } catch {
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = (user as any).accessToken;
        token.role = (user as any).role;
      }
      return token;
    },
    async session({ session, token }) {
      (session as any).accessToken = token.accessToken;
      (session as any).role = token.role;
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
});

export const { GET, POST } = handlers;
