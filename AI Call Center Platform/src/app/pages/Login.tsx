import { useState } from 'react';
import { useNavigate } from 'react-router';
import { Lock, Mail, Loader2, ChevronRight, Layout, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

export function Login() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: 'admin@voiceqa.ai',
    password: 'password'
  });

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/auth/login`, formData);
      
      const { access_token, user } = response.data;
      
      // Store in localStorage
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('user', JSON.stringify(user));
      
      toast.success(`Welcome back, ${user.name}!`);
      
      // Redirect to dashboard
      navigate('/');
      
      // Optional: Refresh the page to ensure all components get the new state
      // window.location.reload(); 
    } catch (error: any) {
      console.error('Login failed:', error);
      const message = error.response?.data?.detail || 'Invalid email or password';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Decorations */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute -top-24 -left-24 size-96 bg-primary/20 rounded-full blur-[100px]" />
        <div className="absolute -bottom-24 -right-24 size-96 bg-violet-500/20 rounded-full blur-[100px]" />
      </div>

      <div className="w-full max-w-md relative animate-in fade-in zoom-in duration-500">
        {/* Logo Section */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center size-16 bg-primary/10 border border-indigo-500/20 rounded-2xl mb-4 shadow-xl shadow-indigo-500/10">
            <Layout className="text-primary" size={32} />
          </div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">VoiceQA AI</h1>
          <p className="text-muted-foreground mt-2">Automated Call Intelligence Platform</p>
        </div>

        {/* Login Card */}
        <div className="bg-card/50 backdrop-blur-xl border border-border rounded-3xl p-8 shadow-2xl">
          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-2">
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider ml-1">Email Address</label>
              <div className="relative group">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                <input 
                  type="email"
                  required
                  value={formData.email}
                  onChange={e => setFormData({ ...formData, email: e.target.value })}
                  placeholder="admin@voiceqa.ai"
                  className="w-full bg-background/50 border border-border rounded-2xl pl-12 pr-4 py-3.5 text-foreground focus:outline-none focus:border-indigo-500/50 transition-all"
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between ml-1">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Password</label>
                <button type="button" className="text-xs text-primary hover:text-indigo-300 font-medium">Forgot?</button>
              </div>
              <div className="relative group">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                <input 
                  type="password"
                  required
                  value={formData.password}
                  onChange={e => setFormData({ ...formData, password: e.target.value })}
                  placeholder="••••••••"
                  className="w-full bg-background/50 border border-border rounded-2xl pl-12 pr-4 py-3.5 text-foreground focus:outline-none focus:border-indigo-500/50 transition-all"
                />
              </div>
            </div>

            <button 
              type="submit"
              disabled={loading}
              className="w-full bg-primary hover:bg-indigo-400 disabled:bg-secondary disabled:text-muted-foreground text-white rounded-2xl py-3.5 font-bold transition-all shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2 group"
            >
              {loading ? <Loader2 className="animate-spin" size={20} /> : (
                <>
                  Sign In 
                  <ChevronRight size={20} className="group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>

          <div className="mt-8 pt-8 border-t border-border text-center">
            <p className="text-muted-foreground text-sm">
              Don't have an account? <button className="text-primary font-semibold hover:text-indigo-300 transition-colors">Request Access</button>
            </p>
          </div>
        </div>

        {/* Footer Info */}
        <div className="mt-8 flex items-center justify-center gap-6 text-[10px] text-muted-foreground font-medium uppercase tracking-widest">
          <div className="flex items-center gap-1.5">
            <ShieldCheck size={12} />
            Enterprise Secure
          </div>
          <div className="flex items-center gap-1.5">
            <Layout size={12} />
            Version 1.0.0
          </div>
        </div>
      </div>
    </div>
  );
}
