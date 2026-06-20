function openPage(pageId) {
  let pages = document.querySelectorAll('.page');
  pages.forEach(p => p.classList.remove('active'));

  document.getElementById(pageId).classList.add('active');

  let sound = document.getElementById('clickSound');
  sound.currentTime = 0;
  sound.play();
}