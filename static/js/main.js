/* ===== LOGIQUE GLOBALE VIDÉO & INTERACTIONS VYBE ===== */

let activeVideoId = null; 
let isMuted = true;

// 1. OBSERVATEUR DE SCROLL (Play/Pause automatique)
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        const video = entry.target.querySelector('video');
        const vibeId = entry.target.getAttribute('data-id'); 

        if (entry.isIntersecting && video) {
            video.play().catch(()=>{});
            activeVideoId = vibeId; 

            // Si le panneau de commentaires est ouvert, on l'actualise
            const panel = document.getElementById("commentPanel");
            if(panel && panel.classList.contains("active")) {
                renderComments(vibeId);
            }
        } else if (video) {
            video.pause();
            video.currentTime = 0;
        }
    });
},{threshold:0.65});

document.querySelectorAll('.vibe-item').forEach(item => observer.observe(item));

// 2. RATIO VIDÉO INTELLIGENT
document.querySelectorAll('video').forEach(video => {
    video.addEventListener('loadedmetadata', () => {
        const ratio = video.videoWidth / video.videoHeight;
        video.style.objectFit = ratio > 1 ? "contain" : "cover";
    });
});

// 3. ACTIONS GLOBALES
function togglePlayPause(v){ v.paused ? v.play() : v.pause(); }

function toggleLike(id){
    const btn = document.getElementById("like-btn-"+id);
    const count = document.getElementById("like-count-"+id);
    if(!btn || !count) return;

    btn.style.transform = "scale(1.3)";
    setTimeout(() => btn.style.transform = "scale(1)", 200);
    btn.classList.toggle("is-liked");
    
    fetch("/like/"+id, {method:"POST"})
        .then(r => r.json())
        .then(d => { if(d) count.innerText = d.likes_count; });
}

function copyLink(id){
    const url = window.location.origin + "/vibe/" + id;
    navigator.clipboard.writeText(url).then(() => {
        alert("Lien de la vibe copié ! 🔗");
    });
}

function toggleFavorite(id){
    const btn = document.getElementById("fav-btn-"+id);
    if(!btn) return;
    fetch("/favorite/"+id, {method:"POST"})
    .then(() => {
        btn.style.color = (btn.style.color === "rgb(241, 196, 15)") ? "white" : "#f1c40f";
    });
}

// 4. GESTION DU SON
document.body.addEventListener('click', ()=>{
    if(isMuted){
        document.querySelectorAll('video').forEach(v => v.muted = false);
        isMuted = false;
    }
},{once:true});