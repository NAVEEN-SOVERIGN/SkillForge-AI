import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BookOpen, Check, Clock3, Compass, Flame, Layers3, Sparkles, Target } from 'lucide-react';
import { useAuth } from '../context/AuthContext.js';
import { useToast } from '../context/ToastContext.js';
import { api } from '../services/api.js';
import { CareerReadinessScore, SkillGapAnalysisResult, RoadmapResult, ProjectRecommendation, LearningActivityLog } from '../types/index.js';
import { BrandMark } from '../components/BrandMark.js';

export const DashboardPage: React.FC = () => {
  const { user, profile } = useAuth();
  const toast = useToast();
  const [readiness, setReadiness] = useState<CareerReadinessScore | null>(null);
  const [gaps, setGaps] = useState<SkillGapAnalysisResult | null>(null);
  const [roadmap, setRoadmap] = useState<RoadmapResult | null>(null);
  const [projects, setProjects] = useState<ProjectRecommendation[]>([]);
  const [activities, setActivities] = useState<LearningActivityLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadDashboardData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [readinessRes, gapsRes, roadmapRes, projectsRes, activitiesRes] = await Promise.all([
        api.readiness.get(), api.analysis.get(), api.roadmap.get(), api.projects.get(), api.activities.getAll()
      ]);
      setReadiness(readinessRes.readiness);
      setGaps(gapsRes.analysis);
      setRoadmap(roadmapRes.roadmap);
      setProjects(projectsRes.projects);
      setActivities(activitiesRes.activities);
    } catch (err: any) {
      toast.error(err.message || 'Failed to load dashboard data.');
    } finally { setIsLoading(false); }
  }, [toast]);

  useEffect(() => { loadDashboardData(); }, [loadDashboardData]);

  if (isLoading) return <main className="workspace-loading" role="status"><span className="workspace-loader" /><strong>Getting your next steps ready…</strong><p>Checking your skills and learning plan</p></main>;

  const missing = (gaps?.items || []).filter(item => item.currentLevel < item.requiredLevel).sort((a, b) => b.priorityScore - a.priorityScore);
  const topGap = missing[0];
  const tasks = (roadmap?.stages || []).flatMap(stage => stage.tasks).filter(task => task.status !== 'completed').slice(0, 3);
  const score = readiness?.overallScore ?? 0;
  const project = projects[0];
  const firstName = (user?.name || profile?.fullName || 'there').trim().split(/\s+/)[0];
  const greeting = new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 18 ? 'Good afternoon' : 'Good evening';

  return (
    <div className="skill-workspace">
      {user?.isDemo && <div className="workspace-demo"><span><b>DEMO SPACE</b> · {user.name}’s sample learning plan</span><span>Explore freely — changes stay on this device</span></div>}
      <header className="workspace-nav">
        <Link to="/dashboard" className="workspace-brand"><span className="workspace-brand-mark"><BrandMark size={28} /></span><span>SkillForge<span className="brand-accent">.</span></span></Link>
        <nav aria-label="Main navigation"><Link className="workspace-nav-current" to="/dashboard">My path</Link><Link to="/roadmap">Learning plan</Link><Link to="/project-forge">Build a project</Link><Link to="/code-context">Code Context</Link></nav>
        <Link to="/profile" className="workspace-profile" aria-label="Open your profile">{firstName.charAt(0).toUpperCase()}</Link>
      </header>

      <main className="workspace-content">
        <section className="workspace-welcome">
          <div className="welcome-copy">
            <div className="workspace-eyebrow"><span className="eyebrow-dot" /> YOUR SKILL JOURNEY</div>
            <h1>{greeting}, {firstName}.<br />Here’s your <em>next move.</em></h1>
            <p>Small, focused steps add up. We’ve picked one good place to start based on your {gaps?.roleTitle || profile?.targetRole || 'career'} goal.</p>
            <div className="welcome-actions"><Link className="workspace-button" to={topGap ? '/roadmap' : '/analysis'}>{topGap ? 'Start learning' : 'Explore your plan'} <ArrowRight size={17} /></Link><Link className="workspace-text-link" to="/analysis">See all skill goals</Link></div>
          </div>
          <div className="welcome-art" aria-hidden="true"><div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" /><div className="art-spark spark-one">✦</div><div className="art-spark spark-two">✳</div><div className="art-tile"><Layers3 size={44} strokeWidth={1.5} /></div><div className="art-caption">ONE STEP<br />AT A TIME</div></div>
        </section>

        <section className="workspace-stats" aria-label="Your progress at a glance">
          <article className="stat-card stat-score"><span className="stat-icon"><Target size={18} /></span><div><strong>{score}<small>/100</small></strong><span>career readiness</span></div><div className="mini-meter"><i style={{ width: `${Math.min(100, Math.max(0, score))}%` }} /></div></article>
          <article className="stat-card"><span className="stat-icon coral-icon"><Compass size={18} /></span><div><strong>{missing.length}</strong><span>skills to focus on</span></div><span className="stat-note">Picked for your goal</span></article>
          <article className="stat-card"><span className="stat-icon lime-icon"><Clock3 size={18} /></span><div><strong>{profile?.weeklyHours ?? 5}<small> hrs</small></strong><span>your weekly learning time</span></div><span className="stat-note">You can change this anytime</span></article>
        </section>

        <div className="workspace-section-heading"><div><span className="workspace-eyebrow">A CLEAR PLACE TO BEGIN</span><h2>Your plan, made simple</h2></div><Link to="/roadmap">Open full plan <ArrowRight size={15} /></Link></div>
        <section className="workspace-plan-grid">
          <article className="start-card">
            <div className="start-card-top"><span className="start-label"><Flame size={15} /> BEST NEXT STEP</span><span className="time-pill"><Clock3 size={14} /> {topGap?.estimatedLearningHours ?? 0} hrs</span></div>
            {topGap ? <><h3>{topGap.name}</h3><p>{topGap.nextRecommendedAction || `Build your ${topGap.name} skills for your target role.`}</p><div className="skill-level-row"><span>Where you are</span><span>Level {topGap.currentLevel} <b>→</b> Level {topGap.requiredLevel}</span></div><div className="level-track"><i style={{ width: `${Math.min(100, (topGap.currentLevel / Math.max(1, topGap.requiredLevel)) * 100)}%` }} /></div><Link to="/roadmap" className="start-card-link">Start this skill <ArrowRight size={16} /></Link></> : <><h3>Keep your momentum</h3><p>Your skill check is looking good. Review your learning plan and choose what you’d like to explore next.</p><Link to="/roadmap" className="start-card-link">Explore your plan <ArrowRight size={16} /></Link></>}
            <div className="start-watermark"><Sparkles size={118} /></div>
          </article>

          <article className="steps-card"><div className="steps-heading"><div><span className="workspace-eyebrow">NO GUESSWORK</span><h3>Your next 3 steps</h3></div><span className="steps-count">{tasks.length || 0} steps</span></div>
            {tasks.length ? <ol className="next-steps">{tasks.map((task, index) => <li key={task.id}><span className={`step-number ${index === 0 ? 'step-active' : ''}`}>{task.status === 'in_progress' ? <span className="step-pulse" /> : String(index + 1).padStart(2, '0')}</span><div className="step-copy"><strong>{task.skillName}</strong><span>{task.stageName} · about {task.estimatedHours} hours</span></div><BookOpen size={16} className="step-book" /></li>)}</ol> : <p className="empty-steps">Your learning plan is ready when you are.</p>}
            <Link to="/roadmap" className="steps-link">See your complete learning plan <ArrowRight size={15} /></Link>
          </article>
        </section>

        <section className="workspace-bottom-grid">
          <article className="build-card"><div className="build-icon"><Layers3 size={20} /></div><div className="build-copy"><span className="workspace-eyebrow">LEARN BY MAKING</span><h3>{project?.title || 'Turn a new skill into something real'}</h3><p>{project ? 'A guided project is ready to help you practise what you learn.' : 'Build a small project, practise your skills, and save the result to your portfolio.'}</p></div><Link to="/project-forge" className="round-arrow" aria-label="Explore projects"><ArrowRight size={19} /></Link></article>
          <article className="activity-card"><div className="activity-card-heading"><span className="workspace-eyebrow">YOUR RECENT WINS</span><Link to="/analytics">View progress <ArrowRight size={14} /></Link></div>{activities.length ? <ul>{activities.slice(0, 2).map(activity => <li key={activity.id}><span className="activity-check"><Check size={14} /></span><div><strong>{activity.title}</strong><span>{activity.details || `${activity.hoursSpent} learning hours`}</span></div></li>)}</ul> : <div className="first-win"><span className="win-spark">✦</span><p>Your first learning session will show up here. <b>You’ve got this.</b></p></div>}</article>
        </section>
        <footer className="workspace-footer"><span>Made for curious builders.</span><span>Need a different starting point? <Link to="/analysis">Explore your skills <ArrowRight size={13} /></Link></span></footer>
      </main>
    </div>
  );
};

export default DashboardPage;
