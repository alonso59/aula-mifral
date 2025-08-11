// Minimal utility to fetch all models from Open WebUI /api/models
// SSR-safe: only runs in browser
export type AggregatedModel = {
  id: string;
  label: string;
  provider: string;
  is_embedding: boolean;
};

export async function fetchAllModels(token = ''): Promise<AggregatedModel[]> {
  if (typeof window === 'undefined') return [];
  try {
    const res = await fetch('/api/models', {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...(token ? { authorization: `Bearer ${token}` } : {})
      }
    });
    if (!res.ok) throw await res.json();
    const json = await res.json();
    // Normalize: { id, label, provider, is_embedding }
    let models: AggregatedModel[] = Array.isArray(json.data) ? json.data.map((m: any) => ({
      id: m.id,
      label: m.label || m.id,
      provider: m.provider || '',
      is_embedding: !!m.is_embedding
    })) : [];
    models = models
      .filter((m: AggregatedModel) => !m.is_embedding)
      .sort((a: AggregatedModel, b: AggregatedModel) => a.provider.localeCompare(b.provider) || a.label.localeCompare(b.label));
    return models;
  } catch (e) {
    console.error('[fetchAllModels] Failed:', e);
    return [];
  }
}
