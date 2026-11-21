import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.js';
import { useToast } from '../context/ToastContext.js';
import { ArrowRight, LogIn, LogOut } from 'lucide-react';
import { BrandMark } from './BrandMark.js';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  return (
    <header className="no-print" style={{ minHeight: 'var(--header-height)', background: 'rgba(238, 245, 238, 0.88)', backdropFilter: 'blur(16px)', borderBottom: '1px solid rgba(23,59,60,.1)', position: 'sticky', top: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', padding: '.65rem clamp(1rem, 4vw, 2rem)' }}>
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '.65rem', color: 'var(--text-primary)', fontWeight: 800, fontSize: '1.15rem', textDecoration: 'none' }}>
        <span className="skillforge-brand-mark"><BrandMark size={25} /></span>
        SkillForge <span style={{ color: 'var(--color-accent)', marginLeft: '-.55rem' }}>AI</span>
      </Link>
      <div style={{ display: 'flex', alignItems: 'center', gap: '.55rem' }}>
        {user ? <><Link to="/code-context" className="btn btn-ghost btn-sm">Code Context</Link><Link to="/dashboard" className="btn btn-secondary btn-sm">Career dashboard</Link><button onClick={() => { logout(); toast.info('Logged out successfully.'); navigate('/'); }} className="btn btn-ghost btn-sm" aria-label="Sign out"><LogOut size={16} /> Sign out</button></> : <>
          <Link to="/auth" className="btn btn-ghost btn-sm"><LogIn size={15} /> Sign in</Link>
          <Link to="/code-context?demo=1&repo=kubernetes%2Fkubernetes&question=Why%20prevent%20concurrent%20eviction%20workers%20for%20the%20same%20pod%3F" className="journey-nav-cta">Try a sample <ArrowRight size={14} /></Link>
        </>}
      </div>
    </header>
  );
};
