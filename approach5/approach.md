Agent
- can spawn Agent(tools=['markdown'])



TASK.md  - userTask
DOUBT.md - append 500 doubts
IDEAS.md - new idea/direction
SOULD.md - soul of agent for this task


i have an idea for creating thinking or pivoting in new directions aka researchign or exploring the ways are: 

1. activley getitn top k from the concept collection.
2. activey gettng topk from the already worked on collection.
3. with that concept try to search in some new direciton , check for new concept
4. cross check that concept is already worked on thing, if yes add to alreayd worked else into idea collections
5. after certiatn idea colleciton has i mean metadaata wtih status count of pending is great that like  3 it show liek we have 3 good idea to work on.
6. now for each idea indivildy start working.
7. this loopoing ensures not doign repeat work, not going fancy, zero hallucination, pure grounded by current world knowledge build on top of papers,articles, great blogs, latest cutting edge techiniques. 


INSTRUCTIONS:
1. Never repeat the same thing you did in past
2. Never redo the task
3. Must be aware on the go about the already done process
4. Must be aware of the direction of work is going exploring or converging.


- chromadb over local file saving as it scales upto 500 documents / search results
- 


Agent
- Spawn N parallel agents 


Take a scenario of 100 page book

TaskAgent( summarize the book)

1. Take an outer quick look
   1. for markdown its check headres, subheaders only
   2. for paragparhed huge content, it spawns per agent to work on content part to create quick look liek section heading or heeading like stuff.



Goal: read full document which is 1 to 1500 lines and get a quick look , thisis done by read block and creating summaries.

Till now done: 
1 to 100 : chromadb answer id : "3f9c2a8e-7b6d-4c1a-9f2e-5a8d3c1b2e4f"
1 to 100 : chromadb answer id : "3f9c2a8e-7b6d-4c1a-9f2e-5a8d3c1b2e4f"
1 to 100 : chromadb answer id : "3f9c2a8e-7b6d-4c1a-9f2e-5a8d3c1b2e4f"
1 to 100 : chromadb answer id : "3f9c2a8e-7b6d-4c1a-9f2e-5a8d3c1b2e4f"
1 to 100 : chromadb answer id : "3f9c2a8e-7b6d-4c1a-9f2e-5a8d3c1b2e4f"

spawns max 4 agents
    SpawnAgent("read 600 to 700 lines and produce 2 line summary")
    SpawnAgent("read 700 to 800 lines and produce 2 line summary")
    SpawnAgent("read 800 to 900 lines and produce 2 line summary")
    SpawnAgent("read 900 to 1000 lines and produce 2 line summary")



LoopAgent helps in looping the task to be completed in tree fashioned subagents.

any long text/ content assume it like  CONTENT.txt

1. first goal is to get a 'Glance of Content' aka for mds we collect headres, section , for paragrpahs


    a. first reads the first 100 lines, not satifies, read next 100 lines .
    b. then spawns the subagent ( 1 to 80 lies get a glance in 2 lines)
    c. now that is gone from memory, that subagent is workign on its own. 
    d. the new agent only knows that previosu agent reported it like it read 200 liesn and spawend 1 to 80. now goal is read from 80 to findout the next meanitnful minimal cut the subagent can work
    e. it reads 80-120, again tool call 120-180, again tool call 180-200.
    f. satisfies and says 80-200 is to work on , so spawn subagent with task saying read 80-120 liesn of content.
    g. it then loops like this, read(filepath/id, startline,endline) is the curiical tool.
    h. it loops by like feedbackiing the new system prompt ( it maintiant teh track, but also nto making the prompt huge, basially like when task is going on instead of writing in prompt like done 1to 20, done 20 to 50, done 50 to 100, it just write done 1-100. make it clearcut. and its the main part that breathes adn makes the life of agent keep going)
    i. it has tail aka child collector, that collects the spawend subagenst all the ids ( as subate work and save there contne tin chromadb and return the ids, just liek hwo funciton returns a string), 
    j. one the feebackign one say aka the prompt has like " Task : DONE " keyword then all the content of the chilids are combined into single content and with new id. and here the birth of the new Agent that now works liek this new id becoens its CONTENT.txt and with the feedbackign oens it picks the next work to do. 
    k. the next one obvilsuly knwos that that content is nothing but the glance and it checks if it can condense it down more or not.
    l. it thern reads and agrees to return the content ( not by readign adn agent saying answer), this apporahc reflects the worked in notebook, aka homework is done and instead of saying i have done the homework in this way to teacher, you show the homework that you wrote well.



