import { getSandbox } from '@cloudflare/sandbox';
export { Sandbox } from '@cloudflare/sandbox'; // Export obrigatório

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Endpoint de API para execução de comandos sandboxed
    if (url.pathname === '/api/exec' && request.method === 'POST') {
      try {
        const body = await request.json();
        const { command, sandboxId = 'default-session' } = body;

        if (!command) {
          return new Response(JSON.stringify({ error: 'Falta o campo command' }), {
            status: 400,
            headers: { 'Content-Type': 'application/json' }
          });
        }

        // Instancia ou recupera a sandbox com o ID especificado
        const sandbox = getSandbox(env.Sandbox, sandboxId);
        
        // Executa o comando na sandbox
        const result = await sandbox.exec(command);

        return new Response(JSON.stringify(result), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }

    // Fallback: se não for a rota da API, o Wrangler automaticamente serve os assets estáticos
    // definidos na pasta "site" configurada em wrangler.jsonc.
    return env.ASSETS.fetch(request);
  }
};
