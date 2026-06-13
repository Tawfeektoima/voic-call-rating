export function buildNotesComposeUrl(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams({ compose: '1' });
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      search.set(key, String(value));
    }
  });
  return `/notes?${search.toString()}`;
}
