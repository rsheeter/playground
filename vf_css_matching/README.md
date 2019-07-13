# CSS Font Matching change suggestions

Google Fonts strives to have users "pay" (in bytes and resulting latency) only for the parts of fonts they actually use. As [CSS3](https://www.w3.org/TR/css-fonts-3/#font-face-rule) puts it "Using CSS font matching rules, a user agent can selectively download only those faces that are needed for a given piece of text."

We are encountering problems with the current [style matching algorithm](https://www.w3.org/TR/css-fonts-4/#font-style-matching) in several areas:

1.  Feature-based matching
1.  Variable font matching on arbitrary axes
1.  Variable font matching for named instances
1.  Matching italic + slant (spec seems to think of them as exclusive choices)

This document outlines potential changes to the style matching algorithm to address each area.

[TOC]

## Matching today
The CSS4 [style matching algorithm](https://www.w3.org/TR/css-fonts-4/#font-style-matching) is roughly:

```
Steps 1-3: Find all the @font-face’s that match by family name.
Step 4: Pick a specific @font-face. A VF is treated as the instance with the best matching characteristics.

4.0 Start with the set of @font-face that match by family name 
4.1 Find the set of faces that match best by width (font-stretch), discard others
    font-stretch supports % so we have fine-grained matching on ‘wdth’
4.2 Find the set of faces that match best by style (font-style), discard others
    font-style can only match 0/1 on ‘ital’ using normal|italic
    oblique has fine grained specification that presumably can match ‘slnt’ 
4.3, 4.4 are curiously not used in spec, omitting here to make #s align
4.5 Find the set of faces that match best by weight (font-weight), discard others
    Font-weight supports int [1,1000] so we have fine-grained matching on ‘wght’
4.6 font-size must be matched within UA-selected tolerance
    TODO what does this actually mean?
4.7 unicode-range; pick the highest priority (declared last) face whose effective character map contains the char
4.8 If no matching face exists or the face doesn’t support the character, try the next family name, starting at Step 1
4.9 If no matching face exists that supports the character, perform UA-specific fallback
4.10 Indicate failure in a UA-specific way, such as by rendering notdef
```

Note that the selection of @font-face is limited to {family name, width, style, weight}; this will come back to bite us below :)

## Matching tomorrow
Wherein potential adjustments to the matching algorithm are outlined :)

We aim to increase the range of scenarios where only the content that is needed gets downloaded.

### Feature based matching

At render-time we know quite a lot about what features of the font are desired. Unfortunately we can't use any of this at matching time. If features could participate in matching we could subset fonts based on feature and match only the ones in use. For example:

```css
// Only downloads if text exists that wants family "A", small-caps
@font-face {
  font-family: “A”;
  font-variant: small-caps;
  src: url(A-small-caps.woff2);
}

// Downloads for any use of A
@font-face {
  font-family: “A”;
  src: url(A.woff2);
}
```

### Variable font axis matching

TODO why is this important? - give the two points on a many dimensional space example, complete variation could be many (5x or more) more bytes.

If we want to deliver two slices of a variable font with different positions on an arbitrary axis we can't match them:

```css
// This face is unreachable: any matching algorithm hit would match both faces
// and then pick the second one (per 4.7)
@font-face {
  font-family: “A”;
  font-variation-settings: “GRAD” 0
}

// If these faces match, this one always wins under rule 4.7
// Equal priority, last declaration wins
@font-face {
  font-family: “A”;
  font-variation-settings: “GRAD” 1
}
```

### Variable font named instance matching
[font-named-instance](https://www.w3.org/TR/css-fonts-4/#font-named-instance) permits a single named instance for an `@font-face`. [feature-variation-precedence](https://www.w3.org/TR/css-fonts-4/#feature-variation-precedence) allows the named instance to be applied.

Named instances do not participate in *matching* at all. This makes use of multiple named instances awkward:

1.  We can't use multiple named instances on an unregistered axis
  1.  For `ital` we can access two positions
1.  We have to matching `@font-face` by other attributes to reach a named instance

Consider this sketch:

```css
// This face is unreachable: any matching algorithm hit would match both faces
// and then pick the second one (per 4.7)
@font-face {
  font-family: “A”;
  font-named-instance: "first";
}

@font-face {
  font-family: “A”;
  font-named-instance: "second";
}

// this is illegal; would be nice if it wasn't
.use-first {
  font-named-instance: "first"
}

// better: full control over fallback using instances
// named-instance (instance-name, family-name), valid in font-family list
.prefer-first {
  font-family: named-instance("first", "A"), "Lobster", named-instance("second", "A");
}

```

Ideally font-named-instance would be legal on all elements and allow multiple values in a fallback chain that included family name at each step (use "Bold" instance of "Roboto", failing that the "Medium" instance of "Open Sans").

On @font-face we would want multiple names as well, either via font-family list or allowing a font-named-instance list.

### Italic and slant
