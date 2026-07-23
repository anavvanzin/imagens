import { createHash, timingSafeEqual } from 'node:crypto';
import { getSandbox } from '@cloudflare/sandbox';
export { Sandbox } from '@cloudflare/sandbox'; // Export obrigatório

const JSON_HEADERS = { 'Content-Type': 'application/json' };

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: JSON_HEADERS,
  });
}

/** Hash then constant-time compare so length of the secret is not leaked. */
function timingSafeEqualSecret(provided, expected) {
  const a = createHash('sha256').update(provided, 'utf8').digest();
  const b = createHash('sha256').update(expected, 'utf8').digest();
  return timingSafeEqual(a, b);
}

/**
 * Require Authorization: Bearer <EXEC_API_KEY>.
 * Fail closed when the secret is unset.
 */
function authorizeExec(request, env) {
  const expected = env.EXEC_API_KEY;
  if (!expected) {
    return jsonResponse({ error: 'Serviço indisponível' }, 503);
  }

  const header = request.headers.get('Authorization') || '';
  const match = /^Bearer\s+(.+)$/i.exec(header);
  if (!match || !timingSafeEqualSecret(match[1], expected)) {
    return jsonResponse({ error: 'Não autorizado' }, 401);
  }

  return null;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Endpoint de API para execução de comandos sandboxed (requer Bearer token)
    if (url.pathname === '/api/exec') {
      if (request.method !== 'POST') {
        return jsonResponse({ error: 'Método não permitido' }, 405);
      }

      const authError = authorizeExec(request, env);
      if (authError) {
        return authError;
      }

      try {
        const body = await request.json();
        const { command, sandboxId = 'default-session' } = body;

        if (!command) {
          return jsonResponse({ error: 'Falta o campo command' }, 400);
        }

        // Instancia ou recupera a sandbox com o ID especificado
        const sandbox = getSandbox(env.Sandbox, sandboxId);

        // Executa o comando na sandbox
        const result = await sandbox.exec(command);

        return jsonResponse(result, 200);
      } catch (err) {
        return jsonResponse({ error: err.message }, 500);
      }
    }

    // Fallback: se não for a rota da API, o Wrangler automaticamente serve os assets estáticos
    // definidos na pasta "site" configurada em wrangler.jsonc.
    return env.ASSETS.fetch(request);
  }
};
