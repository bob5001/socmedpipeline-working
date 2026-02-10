Task Specification: Multi-Agent Social Campaign Pipeline
You are managing a six-agent workflow for social media content generation. Each agent has a specific responsibility. Work through these in order. Dependencies will auto-unlock as tasks complete.
Task 1: Campaign Data Generation
Read the campaign brief from campaign-input.json. Generate a CSV file at posts-queue.csv with these columns: post ID, campaign identifier, campaign section, image prompt, caption, hashtags, image status (pending), vision check status (pending), design status (pending), facebook status (pending). Create at least five realistic posts for a social media campaign. Each post ID should be unique and timestamped. Commit this file to Git with message "Generated campaign posts from brief".
Task 2: Image Generation via API
Read posts-queue.csv. For each row where image status is pending, take the image prompt and send it to Stable Diffusion via Replicate API. Save the generated image to images/{post_id}.png. Update the CSV so that row's image status changes to "generated". Commit with message "Generated images for posts". Do not move forward until all images exist and the CSV is updated.
Task 3: Vision Audit and Approval
Read posts-queue.csv. For each row where image status is generated and vision check status is pending, use Claude's vision capability to examine images/{post_id}.png. Compare it against the image prompt. If it matches the prompt and the tone of the campaign

Task 4: Affinity Designer Text Overlay
Read posts-queue.csv. For each row where vision check status is approved and design status is pending, use the Affinity Designer MCP to open images/{post_id}.png, overlay the caption and hashtags using readable typography, export as images/{post_id}-final.png. Update design status to "complete". Commit with message "Text overlays applied via Affinity Designer". Do not move forward until all designs are complete.
Task 5: Queue Management and Status Tracking
Read posts-queue.csv. Verify all rows have image status as generated, vision check status as approved, and design status as complete. Create a summary report at pipeline-status.json showing total posts, completed posts, any blockers. Update the CSV so facebook status shows ready for all complete posts. Commit with message "Queue verified and ready for posting". This task unlocks the final posting task.
Task 6: Facebook Business Manager Integration
Authenticate to Facebook Business Manager using the limited draft-only user credentials stored in .env. Read posts-queue.csv. For each row where facebook status is ready, create a draft post using the final image at images/{post_id}-final.png, caption, and hashtags. Do not publish, only create drafts. Update facebook status to "draft created". Commit with message "Draft posts created in Facebook Business Manager". When complete, provide a summary of how many drafts were created.
Success Criteria:
All six tasks complete in sequence. Final output is drafts in Facebook Business Manager ready for human review and publishing. No images published to live social media. All work is committed to Git with clear messages.