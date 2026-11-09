let csrf = '';
export function setCSRF(value:string) { csrf = value; }
export class ApiError extends Error { constructor(message:string, public status:number) { super(message); } }

export async function api<T>(path:string, options:RequestInit = {}):Promise<T> {
  const headers = new Headers(options.headers);
  const method = (options.method || 'GET').toUpperCase();
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type','application/json');
  if (!['GET','HEAD'].includes(method) && csrf) headers.set('X-CSRF-Token',csrf);
  let response:Response;
  try { response = await fetch(`/api/v1${path}`, {...options,headers,credentials:'same-origin',cache:'no-store'}); }
  catch { throw new ApiError('Cannot reach the API. Check that the Python and Next.js servers are running.',0); }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = result.detail;
    const message = Array.isArray(detail) ? detail.map((x:{msg:string}) => x.msg).join(' ') : (typeof detail==='string' ? detail : 'Request failed. Please try again.');
    throw new ApiError(message,response.status);
  }
  return result as T;
}
export const post = <T>(path:string,body:unknown = {}) => api<T>(path,{method:'POST',body:JSON.stringify(body)});
export function minor(value:string):number {
  const input=value.trim();
  if (!/^\d+(\.\d{1,2})?$/.test(input)) throw new Error('Use a positive amount with at most two decimal places.');
  const [whole, fraction='']=input.split('.');
  const amount=Number(whole)*100+Number(fraction.padEnd(2,'0'));
  if (!Number.isSafeInteger(amount) || amount<=0 || amount>1000000000) throw new Error('Amount must be between ₱0.01 and ₱10,000,000.');
  return amount;
}
export function money(value:number):string { return new Intl.NumberFormat('en-PH',{style:'currency',currency:'PHP',maximumFractionDigits:2,minimumFractionDigits:0}).format(value/100); }
export function localDate():string { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
export function shortDate(s:string):string { return s ? new Date(s+'T12:00:00').toLocaleDateString('en-PH',{month:'short',day:'numeric',year:'numeric'}) : 'No due date'; }
