// The menu bar stays on top while scrolling (site.css). Once the bottom of the header's icon has gone behind the bar,
// the next RANGE pixels of scrolling set --p from 0 to 1: the bar's icon fades in and the menu narrows. Before that
// line the bar has no icon and the menu is full width, so the two icons are never seen together.
const RANGE = 32;
const logo = document.querySelector('header.top > img');
const bar = document.querySelector('.sbar');
if (logo && bar) {
  let pending = false;
  const update = () => {
    pending = false;
    const p = Math.min(1, Math.max(0, (bar.offsetHeight - logo.getBoundingClientRect().bottom) / RANGE));
    document.documentElement.style.setProperty('--p', p.toFixed(3));
  };
  const schedule = () => {
    if (!pending) { pending = true; requestAnimationFrame(update); }
  };
  addEventListener('scroll', schedule, {passive: true});
  addEventListener('resize', schedule);
  update();
}
