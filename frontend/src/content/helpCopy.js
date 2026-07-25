export const HELP_COPY = {
  title: 'How AgentGuard works',
  blurb: [
    'AgentGuard watches your agent’s web traffic, flags risky behavior, and saves sessions so you can review what happened.',
    'On Guard, pick an agent and turn protection on. Then check Sessions for activity and Rules to see how scoring works.',
  ],
  tourButtonLabel: 'Guided tour',
  closeLabel: 'Close help',
};

export const TOUR_STEPS = [
  {
    id: 'nav-guard',
    route: '/',
    selector: '[data-tour="nav-guard"]',
    title: 'Guard',
    body: 'Start here when you want to protect your agent.',
  },
  {
    id: 'agent',
    route: '/',
    selector: '[data-tour="agent"]',
    title: 'Choose an agent',
    body: 'Select the agent you want AgentGuard to watch.',
  },
  {
    id: 'power',
    route: '/',
    selector: '[data-tour="power"]',
    title: 'Turn Guard on',
    body: 'Press the power button to turn protection on or off.',
  },
  {
    id: 'nav-sessions',
    route: '/sessions',
    selector: '[data-tour="nav-sessions"]',
    title: 'Sessions',
    body: 'After protection is on, come here to see what AgentGuard recorded.',
  },
  {
    id: 'sessions-main',
    route: '/sessions',
    selector: '[data-tour="sessions-main"]',
    title: 'Review activity',
    body: 'Open a session to explore events, risk scores, and what the agent did.',
  },
  {
    id: 'nav-rules',
    route: '/rules',
    selector: '[data-tour="nav-rules"]',
    title: 'Rules',
    body: 'These are the rules AgentGuard uses when it scores risk.',
  },
  {
    id: 'rules-main',
    route: '/rules',
    selector: '[data-tour="rules-main"]',
    title: 'Browse rules',
    body: 'See which rules are on and how each one affects the score.',
  },
  {
    id: 'finish',
    route: '/',
    selector: null,
    title: 'You’re ready',
    body: 'You’re all set. Open Help next to the AgentGuard logo anytime you want a refresher.',
  },
];
