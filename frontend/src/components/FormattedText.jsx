export default function FormattedText({ text }) {
  const formatted = formatText(text)
  return (
    <div className="text-sm leading-relaxed whitespace-pre-wrap text-left">
      {formatted}
    </div>
  )
}

function formatText(text) {
  let result = text

  // 1. Convert *emphasis* or **emphasis** to CAPS (remove asterisks)
  result = result.replace(/\*{1,2}([^*]+)\*{1,2}/g, (match, content) => {
    // Heuristic: short phrases (under ~4 words) = emphasis → caps
    // Longer bolded phrases are likely headings, handled separately below
    if (content.trim().split(/\s+/).length <= 4 && !content.trim().endsWith(":")) {
      return content.toUpperCase()
    }
    return content  // leave headings alone, handled in step 2
  })

  // 2. Handle headings: **Heading:** on its own line, rest of text follows on new line
  result = result.replace(/\*\*([^*]+:)\*\*\s*/g, (match, heading) => {
    return `\n${heading.toUpperCase()}\n`
  })

  // 3. Ensure numbered points break onto new lines: "1) text 2) text" → separate lines
  result = result.replace(/(\d\))\s*/g, '\n$1 ')

  // 4. Clean up leading/trailing whitespace and collapse triple+ newlines
  result = result.replace(/\n{3,}/g, '\n\n').trim()

  return result
}