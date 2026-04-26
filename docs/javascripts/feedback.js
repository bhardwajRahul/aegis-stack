// Page feedback with Plausible custom events
document.addEventListener("DOMContentLoaded", function() {
  const feedback = document.querySelector(".md-feedback");
  if (!feedback) return;

  feedback.querySelectorAll("button").forEach(function(button) {
    button.addEventListener("click", function() {
      const value = this.getAttribute("data-md-value");

      // Send to Plausible
      if (window.plausible) {
        plausible("Feedback", {
          props: {
            page: window.location.pathname,
            rating: value === "1" ? "helpful" : "not_helpful"
          }
        });
      }

      // Show confirmation
      const note = feedback.querySelector(".md-feedback__note");
      note.textContent = "Thanks for your feedback!";
      feedback.querySelectorAll("button").forEach(b => b.disabled = true);

      // Auto-dismiss after 3 seconds
      setTimeout(function() {
        note.textContent = "";
      }, 3000);
    });
  });
});
