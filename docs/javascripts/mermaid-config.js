// Mermaid configuration for high-resolution diagrams
document.addEventListener('DOMContentLoaded', function() {
  mermaid.initialize({
    startOnLoad: true,
    theme: 'default',
    themeVariables: {
      // Increase font sizes for better readability
      fontSize: '16px',
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',

      // Colors for better contrast
      primaryColor: '#e8f5e8',
      primaryTextColor: '#1b5e20',
      primaryBorderColor: '#2e7d32',
      lineColor: '#424242',

      // Node spacing for larger diagrams
      nodeTextSize: '16px',
      edgeLabelBackground: '#ffffff',
    },

    // Flowchart configuration
    flowchart: {
      useMaxWidth: true,
      htmlLabels: true,
      rankSpacing: 80,        // Increased spacing between ranks
      nodeSpacing: 50,        // Increased spacing between nodes
      curve: 'linear',
      padding: 20,
    },

    // Sequence diagram configuration
    sequence: {
      useMaxWidth: true,
      diagramMarginX: 30,
      diagramMarginY: 30,
      actorMargin: 60,        // Increased actor spacing
      width: 200,             // Increased actor width
      height: 80,             // Increased actor height
      boxMargin: 15,
      boxTextMargin: 8,
      noteMargin: 15,
      messageMargin: 50,      // Increased message spacing
      messageAlign: 'center',
      mirrorActors: true,
      bottomMarginAdj: 1,
      useMaxWidth: true,
      rightAngles: false,
      showSequenceNumbers: false,
    },

    // Graph configuration
    graph: {
      useMaxWidth: true,
      htmlLabels: true,
    },

    // Security settings
    securityLevel: 'loose',

    // Enable larger diagrams
    maxTextSize: 90000,
    maxEdges: 2000,
  });
});