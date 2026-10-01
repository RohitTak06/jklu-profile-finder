"use client";

import { ChangeEvent, DragEvent, FormEvent, useEffect, useRef, useState } from "react";
import Image from "next/image";

const MAX_FILE_BYTES = 10 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

type AuthMode = "login" | "register";

function csrfToken(): string {
  const value = document.cookie.split("; ").find((cookie) => cookie.startsWith("csrf_token="));
  return value ? decodeURIComponent(value.slice("csrf_token=".length)) : "";
}

export default function Home() {
  const fileInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [account, setAccount] = useState("");
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [authOpen, setAuthOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [message, setMessage] = useState("");
  const [messageKind, setMessageKind] = useState<"error" | "notice">("notice");

  useEffect(() => {
    void fetch("/api/v1/auth/me", { credentials: "include" })
      .then(async (response) => {
        if (response.ok) {
          const user = (await response.json()) as { email: string };
          setAccount(user.email);
        }
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  function chooseFile(candidate?: File) {
    if (!candidate) return;
    if (!ACCEPTED_TYPES.includes(candidate.type) || candidate.size > MAX_FILE_BYTES) {
      setMessage("Choose a JPG, PNG or WEBP image under 10 MB.");
      setMessageKind("error");
      return;
    }
    setFile(candidate);
    setPreviewUrl(URL.createObjectURL(candidate));
    setMessage("");
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    chooseFile(event.target.files?.[0]);
    event.target.value = "";
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    chooseFile(event.dataTransfer.files[0]);
  }

  async function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setMessage("");
    const body = new FormData();
    body.append("image", file);
    try {
      const response = await fetch("/api/v1/search", {
        method: "POST",
        credentials: "include",
        headers: { "X-CSRF-Token": csrfToken() },
        body,
      });
      const result = (await response.json()) as { detail?: string };
      if (response.status === 401) {
        setAuthOpen(true);
        setMessage("Sign in to start a search. Your photo is only sent after you choose Find a profile.");
        setMessageKind("notice");
      } else if (response.status === 503) {
        setMessage("The authorized JKLU profile index is not connected yet. Your photo was not retained.");
        setMessageKind("notice");
      } else if (!response.ok) {
        setMessage(result.detail ?? "We could not process this image. Please try another photo.");
        setMessageKind("error");
      }
    } catch {
      setMessage("The search service could not be reached. Please try again shortly.");
      setMessageKind("error");
    } finally {
      setBusy(false);
    }
  }

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`/api/v1/auth/${authMode === "register" ? "register" : "login"}`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const result = (await response.json()) as { email?: string; detail?: string };
      if (!response.ok) throw new Error(result.detail ?? "Unable to sign in.");
      setAccount(result.email ?? email);
      setAuthOpen(false);
      setPassword("");
      setMessage("You are signed in. Add one photo when you are ready.");
      setMessageKind("notice");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to sign in.");
      setMessageKind("error");
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    await fetch("/api/v1/auth/logout", {
      method: "POST",
      credentials: "include",
      headers: { "X-CSRF-Token": csrfToken() },
    });
    setAccount("");
    setMessage("You have signed out.");
  }

  function clearImage() {
    setFile(null);
    setPreviewUrl("");
    setMessage("");
  }

  return (
    <main className="site-shell">
      <header className="topbar">
        <a className="wordmark" href="#top" aria-label="JKLU Profile Finder home">
          <span className="brand-mark" aria-hidden="true"><span /></span>
          <span>JKLU <b>Profile Finder</b></span>
        </a>
        <div className="topbar-right">
          <span className="scope-label"><span className="live-dot" /> JKLU INDEX</span>
          {account ? (
            <button className="account-button" onClick={() => void signOut()} type="button">
              <span className="account-avatar">{account.slice(0, 1).toUpperCase()}</span>
              <span className="account-email">{account}</span>
              <span className="sign-out-label">Sign out</span>
            </button>
          ) : (
            <button className="sign-in-button" onClick={() => setAuthOpen((open) => !open)} type="button">
              Sign in <span aria-hidden="true">↗</span>
            </button>
          )}
        </div>
      </header>

      <section className="intro" id="top">
        <div className="intro-copy">
          <p className="eyebrow"><span>01</span> CAMPUS PROFILE DISCOVERY</p>
          <h1>A face from campus.<br /><em>A profile, possibly.</em></h1>
          <p className="intro-description">
            Add one photo to look for a possible match in the authorized JKLU profile index.
            Every result needs supporting evidence; no match is ever a certainty.
          </p>
          <div className="trust-line">
            <span className="trust-icon" aria-hidden="true">✓</span>
            Consent-based index only
            <span className="trust-divider" />
            No public-web face search
          </div>
        </div>
        <div className="campus-stamp" aria-hidden="true">
          <span>JAIPUR</span>
          <strong>JKLU</strong>
          <span>26°49&apos; N · 75°53&apos; E</span>
        </div>
      </section>

      <section className="workspace" aria-label="Photo profile search">
        <div className="section-heading">
          <div>
            <p className="eyebrow"><span>02</span> NEW SEARCH</p>
            <h2>Start with a photo</h2>
          </div>
          <p className="section-note">One image. Nothing else.</p>
        </div>

        <form onSubmit={submitSearch}>
          <input
            ref={fileInput}
            className="visually-hidden"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={onFileChange}
            tabIndex={-1}
            aria-hidden="true"
          />
          <div className="upload-wrap">
            <div
              className={`upload-zone${dragging ? " is-dragging" : ""}${file ? " has-file" : ""}`}
              role="button"
              tabIndex={0}
              onClick={() => fileInput.current?.click()}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  fileInput.current?.click();
                }
              }}
              onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              aria-label={file ? `Selected image: ${file.name}. Choose another photo` : "Choose or drop one photo"}
            >
              {previewUrl ? (
                <Image className="image-preview" src={previewUrl} alt="Selected photo preview" width={82} height={112} unoptimized />
              ) : (
                <span className="upload-glyph" aria-hidden="true">
                  <svg viewBox="0 0 48 48" fill="none">
                    <path d="M24 32V8m0 0-8 8m8-8 8 8M9 29v10h30V29" />
                  </svg>
                </span>
              )}
              <span className="upload-copy">
                <strong>{file ? file.name : "Drop a photo here"}</strong>
                <span>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB · Select to replace` : "or browse your files"}</span>
              </span>
              {!file && <span className="file-formats">JPG&nbsp; / &nbsp;PNG&nbsp; / &nbsp;WEBP</span>}
            </div>
            {file && (
              <button
                className="remove-image"
                type="button"
                aria-label="Remove selected photo"
                onClick={clearImage}
              >
                ×
              </button>
            )}
          </div>

          <div className="upload-footer">
            <p className="privacy-note">
              <span aria-hidden="true">⌑</span>
              Photo is processed temporarily and not retained.
            </p>
            <button className="search-button" type="submit" disabled={!file || busy}>
              {busy ? "Checking…" : "Find a profile"}
              {!busy && <span aria-hidden="true">↗</span>}
            </button>
          </div>
        </form>

        {message && (
          <div className={`notice ${messageKind}`} role="status">
            <span className="notice-mark" aria-hidden="true">{messageKind === "error" ? "!" : "i"}</span>
            <p>{message}</p>
            {message.includes("not connected") && <span className="notice-tag">INDEX OFFLINE</span>}
          </div>
        )}

        {authOpen && !account && (
          <section className="auth-panel" aria-labelledby="auth-heading">
            <div className="auth-heading-row">
              <div>
                <p className="eyebrow"><span>03</span> YOUR ACCOUNT</p>
                <h2 id="auth-heading">{authMode === "login" ? "Welcome back" : "Create your account"}</h2>
              </div>
              <button className="close-button" type="button" onClick={() => setAuthOpen(false)} aria-label="Close sign-in form">×</button>
            </div>
            <form className="auth-form" onSubmit={submitAuth}>
              <label htmlFor="email">Email address</label>
              <input id="email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
              <label htmlFor="password">Password</label>
              <input id="password" type="password" autoComplete={authMode === "login" ? "current-password" : "new-password"} minLength={12} required value={password} onChange={(event) => setPassword(event.target.value)} />
              <button className="search-button auth-submit" type="submit" disabled={busy}>
                {busy ? "Please wait…" : authMode === "login" ? "Sign in" : "Create account"}
                {!busy && <span aria-hidden="true">↗</span>}
              </button>
            </form>
            <button className="mode-switch" type="button" onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}>
              {authMode === "login" ? "New here? Create an account" : "Already registered? Sign in"}
            </button>
          </section>
        )}
      </section>

      <footer className="page-footer">
        <span>JKLU PROFILE FINDER <span className="footer-separator">/</span> JAIPUR, INDIA</span>
        <span>Possible matches only. Evidence over certainty.</span>
      </footer>
    </main>
  );
}
