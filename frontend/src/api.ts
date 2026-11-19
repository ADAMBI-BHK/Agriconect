const HEADERS = { "X-Requested-With": "agriconnect" };

async function parse(res: Response) {
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = (data as any).detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map((e: any) => e.msg).join(", ") : "Erreur " + res.status);
  }
  return data;
}

export async function api(path: string, method = "GET", body?: unknown) {
  const res = await fetch("/api" + path, {
    method, credentials: "include",
    headers: { "Content-Type": "application/json", ...HEADERS },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return parse(res);
}

/** Envoi de fichier (multipart). Ne pas fixer Content-Type : le navigateur ajoute la frontière. */
export async function upload(path: string, form: FormData) {
  return parse(await fetch("/api" + path, { method: "POST", credentials: "include", headers: HEADERS, body: form }));
}

/** Téléchargement d'un fichier protégé (cookie de session) puis enregistrement local. */
export async function download(path: string, filename: string) {
  const res = await fetch("/api" + path, { credentials: "include", headers: HEADERS });
  if (!res.ok) { await parse(res); return; }
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export function saveText(filename: string, text: string, mime = "text/csv;charset=utf-8") {
  const url = URL.createObjectURL(new Blob(["\ufeff" + text], { type: mime }));
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
