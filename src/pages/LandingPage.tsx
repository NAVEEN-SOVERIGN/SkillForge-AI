import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowDown, ArrowRight, GitBranch, Search, ShieldCheck, Sparkles, Waypoints } from 'lucide-react';
import { Navbar } from '../components/Navbar.js';

const sampleLink = '/code-context?demo=1&repo=kubernetes%2Fkubernetes&question=Why%20prevent%20concurrent%20eviction%20workers%20for%20the%20same%20pod%3F';

export const LandingPage: React.FC = () => (
  <div className="journey-landing">
    <Navbar />
    <main>
      <section className="journey-hero">
        <div className="journey-orbit journey-orbit-a" /><div className="journey-orbit journey-orbit-b" />
        <div className="journey-hero-copy">
          <span className="journey-kicker"><Sparkles size={14} /> CODE HAS A MEMORY. LET’S FIND IT.</span>
          <h1>Every line has a past.<br /><em>Ask what happened.</em></h1>
          <p>SkillForge follows a codebase’s history to find the decisions behind the code—and shows you the receipts.</p>
          <div className="journey-hero-actions"><Link to={sampleLink} className="journey-primary">Walk through a live example <ArrowRight size={17} /></Link><a href="#how-it-works" className="journey-secondary">How it works <ArrowDown size={15} /></a></div>
          <span className="journey-no-account"><span /> Start with a public GitHub repository · No account needed</span>
        </div>
        <div className="journey-visual" aria-label="Repository history connected to decisions and code"><div className="visual-glow" /><div className="visual-orbit orbit-a" /><div className="visual-orbit orbit-b" /><div className="visual-node node-repo"><GitBranch size={19} /><span>repository</span></div><div className="visual-node node-decision"><Waypoints size={20} /><span>decision</span></div><div className="visual-node node-code"><span className="code-mark">{ }</span><span>code</span></div><div className="visual-connector connector-one" /><div className="visual-connector connector-two" /><div className="visual-center"><span>WHY</span><Sparkles size={24} /></div><div className="visual-note">follow the evidence ↗</div></div>
      </section>

      <section className="journey-how" id="how-it-works">
        <div className="journey-section-intro"><span className="journey-step-label">A SMALL TOUR · ABOUT 30 SECONDS</span><h2>From a question to its source.</h2><p>No setup guide to read first. We’ll walk you through one real repository.</p></div>
        <div className="journey-steps">
          {[
            { number: '01', icon: GitBranch, title: 'Open a real codebase', text: 'We start you with Kubernetes so you can explore right away. Or paste any public GitHub repository.' },
            { number: '02', icon: Search, title: 'Ask a plain question', text: 'Try “Why did this change?” or ask about a file, behavior, or design choice.' },
            { number: '03', icon: ShieldCheck, title: 'Check the receipts', text: 'See the matching discussion, author, date, and source link. If history is silent, we say so.' }
          ].map(({ number, icon: Icon, title, text }) => <article className="journey-step" key={number}><span className="journey-step-number">{number}</span><span className="journey-step-icon"><Icon size={19} /></span><h3>{title}</h3><p>{text}</p><span className="journey-step-dash" /></article>)}
        </div>
        <div className="journey-bottom-cta"><div><span className="journey-step-label">READY WHEN YOU ARE</span><h2>Let’s follow one decision.</h2></div><Link to={sampleLink} className="journey-primary">Start the example <ArrowRight size={17} /></Link></div>
      </section>
      <footer className="journey-footer"><span>SkillForge <b>Code Context</b></span><span>Decisions, connected to the code they shaped.</span></footer>
    </main>
  </div>
);

export default LandingPage;
