export class ApiClient {
  constructor(baseURL = null) {
    this.baseURL = baseURL || (location.hostname === 'localhost' ? 'http://localhost:5000/api' : '/api');
    this.idToken = null;
  }
  async setUser(user) { this.idToken = user ? await user.getIdToken() : null; }
  headers() {
    const h = {'Content-Type':'application/json'};
    if (this.idToken) h['Authorization'] = `Bearer ${this.idToken}`;
    return h;
  }
  async get(path)  { const r = await fetch(this.baseURL+path, {headers:this.headers()}); return r.json(); }
  async post(path, body) { const r = await fetch(this.baseURL+path, {method:'POST',headers:this.headers(), body: JSON.stringify(body||{})}); return r.json(); }
}
window.apiClient = new ApiClient();
